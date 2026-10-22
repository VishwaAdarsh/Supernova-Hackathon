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
from urllib.parse import urlparse, urlunparse
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2 import extras
    from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

ROOT = Path(__file__).resolve().parent.parent

# Resolve SQLite database path (supports persistent disk mount via DATA_DIR or RENDER_DISK_PATH)
custom_data_dir = os.environ.get('DATA_DIR') or os.environ.get('RENDER_DISK_PATH')
if custom_data_dir:
    DATABASE_DIR = Path(custom_data_dir).resolve()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_PATH = (DATABASE_DIR / 'registrations.db').resolve()
else:
    DATABASE_DIR = (ROOT / 'database').resolve()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_PATH = (DATABASE_DIR / 'registrations.db').resolve()

# Unified exception classes
class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class IntegrityError(DatabaseError):
    """Raised on unique constraint or foreign key violations."""
    pass

def get_database_url():
    """Returns sanitized PostgreSQL connection string if configured in environment."""
    url = (
        os.environ.get('DATABASE_URL') or 
        os.environ.get('SUPABASE_DB_URL') or 
        os.environ.get('POSTGRES_URL')
    )
    if not url:
        return None
    url = url.strip()
    # Normalize postgres:// scheme for psycopg2 compatibility
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]

    # Auto-convert Supabase direct URL (IPv6 only) to IPv4 Supavisor connection pooler
    # This prevents [Errno 101] Network is unreachable on Render, AWS, and IPv4-only hosts
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ''
        m_supa = re.match(r'^db\.([a-z0-9]+)\.supabase\.co$', hostname)
        if m_supa:
            project_ref = m_supa.group(1)
            region = os.environ.get('SUPABASE_REGION', 'ap-northeast-1').strip()
            pooler_host = f"aws-0-{region}.pooler.supabase.com"
            username = parsed.username or 'postgres'
            if not username.endswith(f".{project_ref}"):
                username = f"{username}.{project_ref}"
            password = parsed.password or ''
            pooler_port = parsed.port if (parsed.port and parsed.port != 5432) else 6543
            netloc = f"{username}:{password}@{pooler_host}:{pooler_port}" if password else f"{username}@{pooler_host}:{pooler_port}"
            path = parsed.path or '/postgres'
            query = parsed.query or 'sslmode=require'
            if 'sslmode' not in query:
                query += '&sslmode=require'
            url = urlunparse((parsed.scheme, netloc, path, parsed.params, query, parsed.fragment))
    except Exception as e:
        print(f"[DATABASE WARNING] Could not parse/transform DATABASE_URL: {e}")

    # Ensure sslmode is present if connecting to remote Supabase/Render Postgres
    if 'sslmode' not in url and ('supabase' in url or 'render' in url or 'pooler' in url):
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}sslmode=require"
    return url

def is_postgres(conn=None):
    """True if connection is PostgreSQL, or if PostgreSQL is configured and driver is available."""
    if conn is not None:
        return getattr(conn, 'is_postgres', False)
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
        if q.upper().startswith('BEGIN IMMEDIATE') or q.upper() == 'BEGIN':
            q = 'BEGIN'
        # Replace ? with %s for psycopg2 parameter substitution
        q = re.sub(r'\?', '%s', q)
        return q

    def _convert_params(self, params):
        if params is None:
            return None
        converted = []
        for p in params:
            if isinstance(p, (bytes, bytearray)):
                converted.append(psycopg2.Binary(p))
            else:
                converted.append(p)
        return tuple(converted) if isinstance(params, tuple) else converted

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._cursor.close()
        except Exception:
            pass

    def __iter__(self):
        cols = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
        for row in self._cursor:
            yield HybridRow(row, cols)

    def execute(self, query, params=None):
        converted = self._convert_query(query)
        converted_params = self._convert_params(params)
        try:
            if converted_params is None:
                self._cursor.execute(converted)
            else:
                self._cursor.execute(converted, converted_params)
            return self
        except psycopg2.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except psycopg2.Error as e:
            raise DatabaseError(str(e)) from e

    def executemany(self, query, seq_of_params):
        converted = self._convert_query(query)
        converted_seq = [self._convert_params(p) for p in seq_of_params]
        try:
            self._cursor.executemany(converted, converted_seq)
            return self
        except psycopg2.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except psycopg2.Error as e:
            raise DatabaseError(str(e)) from e

    def fetchone(self):
        if self._cursor.description is None:
            return None
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self._cursor.description]
        return HybridRow(row, cols)

    def fetchmany(self, size=None):
        if self._cursor.description is None:
            return []
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        if not rows:
            return []
        cols = [desc[0] for desc in self._cursor.description]
        return [HybridRow(r, cols) for r in rows]

    def fetchall(self):
        if self._cursor.description is None:
            return []
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [desc[0] for desc in self._cursor.description]
        return [HybridRow(r, cols) for r in rows]

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    @property
    def lastrowid(self):
        return getattr(self._cursor, 'lastrowid', None)


class PostgresConnectionWrapper:
    """Wraps a psycopg2 connection to mimic sqlite3.Connection context behavior."""
    is_postgres = True

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

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor())

    def execute(self, query, params=None):
        cur = self._conn.cursor()
        wrapper = PostgresCursorWrapper(cur)
        return wrapper.execute(query, params)

    def executemany(self, query, seq_of_params):
        cur = self._conn.cursor()
        wrapper = PostgresCursorWrapper(cur)
        return wrapper.executemany(query, seq_of_params)

    def executescript(self, script):
        with self._conn.cursor() as cur:
            cur.execute(script)
        self._conn.commit()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def row_factory(self):
        return None

    @row_factory.setter
    def row_factory(self, val):
        pass


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
