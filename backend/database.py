"""
SUPERNOVA 2026 - Unified Database & Storage Adapter
Provides seamless dual-mode connectivity:
1. Supabase PostgreSQL (Production on Render) via DATABASE_URL / SUPABASE_DB_URL
2. Local SQLite (Development & Offline Testing) via database/registrations.db
3. Supabase Private Storage for persistent payment proof uploads
"""
import os
import re
import io
import json
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2 import extras
    from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT / 'database'
SQLITE_PATH = (DATABASE_DIR / 'registrations.db') if (DATABASE_DIR / 'registrations.db').exists() else (ROOT / 'registrations.db')

# Unified exception classes
class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class IntegrityError(DatabaseError):
    """Raised on unique constraint or foreign key violations."""
    pass

def get_database_url():
    """Returns PostgreSQL connection string if configured in environment."""
    return (
        os.environ.get('DATABASE_URL') or 
        os.environ.get('SUPABASE_DB_URL') or 
        os.environ.get('POSTGRES_URL')
    )

def is_postgres():
    """True if configured to use PostgreSQL and driver is available."""
    return bool(get_database_url()) and HAS_PSYCOPG2

def get_supabase_credentials():
    """Returns (supabase_url, service_role_key) if configured."""
    url = os.environ.get('SUPABASE_URL') or os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
    key = (
        os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or 
        os.environ.get('SUPABASE_KEY') or 
        os.environ.get('SUPABASE_SERVICE_KEY')
    )
    return url.rstrip('/') if url else None, key


class HybridRow(dict):
    """
    Dict-like row object that supports both column name lookup (row['id'])
    and index lookup (row[0]), matching sqlite3.Row behavior.
    """
    def __init__(self, values, columns):
        super().__init__(zip(columns, values))
        self._values = list(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class PostgresCursorWrapper:
    """Wraps a psycopg2 cursor to translate SQLite queries and return HybridRows."""
    def __init__(self, cursor):
        self._cursor = cursor

    def _convert_query(self, query):
        q = query.strip()
        # Handle SQLite-specific transaction statements
        if q.upper().startswith('BEGIN IMMEDIATE'):
            q = 'BEGIN'
        # Replace ? with %s for psycopg2 parameter substitution
        # Only replace ? when not inside string literals
        q = re.sub(r'\?', '%s', q)
        return q

    def execute(self, query, params=None):
        converted = self._convert_query(query)
        try:
            if params is None:
                self._cursor.execute(converted)
            else:
                self._cursor.execute(converted, params)
            return self
        except psycopg2.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except psycopg2.Error as e:
            raise DatabaseError(str(e)) from e

    def executemany(self, query, seq_of_params):
        converted = self._convert_query(query)
        try:
            self._cursor.executemany(converted, seq_of_params)
            return self
        except psycopg2.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except psycopg2.Error as e:
            raise DatabaseError(str(e)) from e

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self._cursor.description]
        return HybridRow(row, cols)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [desc[0] for desc in self._cursor.description]
        return [HybridRow(r, cols) for r in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description


class PostgresConnectionWrapper:
    """Wraps a psycopg2 connection to mimic sqlite3.Connection context behavior."""
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._conn.close()

    def execute(self, query, params=None):
        cur = self._conn.cursor()
        wrapper = PostgresCursorWrapper(cur)
        return wrapper.execute(query, params)

    def executemany(self, query, seq_of_params):
        cur = self._conn.cursor()
        wrapper = PostgresCursorWrapper(cur)
        return wrapper.executemany(query, seq_of_params)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


@contextmanager
def get_db_connection():
    """
    Context manager that yields a database connection.
    Automatically chooses PostgreSQL (if configured) or SQLite.
    """
    db_url = get_database_url()
    if db_url and HAS_PSYCOPG2:
        try:
            conn = psycopg2.connect(db_url, connect_timeout=15)
            wrapper = PostgresConnectionWrapper(conn)
            yield wrapper
            return
        except Exception as e:
            # Fall back to SQLite if remote Postgres is unreachable
            print(f"[DATABASE WARNING] Failed to connect to PostgreSQL ({e}). Falling back to SQLite.")

    # SQLite fallback
    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def connect():
    """
    Returns an active database connection for direct use.
    Compatible with existing `with connect() as db:` pattern.
    """
    db_url = get_database_url()
    if db_url and HAS_PSYCOPG2:
        try:
            conn = psycopg2.connect(db_url, connect_timeout=15)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print(f"[DATABASE WARNING] PostgreSQL connect failed ({e}). Using SQLite fallback.")

    conn = sqlite3.connect(SQLITE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


# --- Supabase Storage Helpers ---

def upload_proof_to_supabase(filename: str, file_bytes: bytes, content_type: str = 'image/jpeg') -> str | None:
    """
    Uploads a payment screenshot to the private 'payment-proofs' Supabase Storage bucket.
    Returns storage path identifier (e.g. 'supabase://payment-proofs/filename') or None on error.
    """
    url, key = get_supabase_credentials()
    if not url or not key:
        return None

    endpoint = f"{url}/storage/v1/object/payment-proofs/{filename}"
    req = urllib.request.Request(
        endpoint,
        data=file_bytes,
        headers={
            'Authorization': f'Bearer {key}',
            'apiKey': key,
            'Content-Type': content_type,
            'x-upsert': 'true'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                return f"supabase://payment-proofs/{filename}"
    except Exception as e:
        print(f"[STORAGE ERROR] Failed to upload proof to Supabase Storage: {e}")
    return None


def fetch_proof_from_supabase(storage_path: str) -> tuple[bytes, str] | None:
    """
    Fetches a private proof image from Supabase Storage using service role credentials.
    Returns (bytes, content_type) or None on failure.
    """
    url, key = get_supabase_credentials()
    if not url or not key or not storage_path.startswith('supabase://payment-proofs/'):
        return None

    filename = storage_path.replace('supabase://payment-proofs/', '').strip('/')
    endpoint = f"{url}/storage/v1/object/authenticated/payment-proofs/{filename}"
    req = urllib.request.Request(
        endpoint,
        headers={
            'Authorization': f'Bearer {key}',
            'apiKey': key
        },
        method='GET'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                raw_bytes = resp.read()
                content_type = resp.headers.get('Content-Type', 'image/jpeg')
                return raw_bytes, content_type
    except Exception as e:
        print(f"[STORAGE ERROR] Failed to fetch proof from Supabase Storage: {e}")
    return None
