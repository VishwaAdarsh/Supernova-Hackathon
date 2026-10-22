"""
SUPERNOVA 2026 - Unified Database & Storage Adapter
Provides reliable, single-authoritative-database persistence:
1. Supabase PostgreSQL (Production on Render) via DATABASE_URL / SUPABASE_DB_URL
2. Local Persistent SQLite (Development / Render Persistent Disk) via database/registrations.db
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

# Resolve SQLite database path (supports persistent disk mount via DATA_DIR, RENDER_DISK_PATH, or PERSISTENT_STORAGE_PATH)
custom_data_dir = os.environ.get('DATA_DIR') or os.environ.get('RENDER_DISK_PATH') or os.environ.get('PERSISTENT_STORAGE_PATH')
if custom_data_dir:
    DATABASE_DIR = Path(custom_data_dir).resolve()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_PATH = (DATABASE_DIR / 'registrations.db').resolve()
    IS_PERSISTENT_DISK = True
else:
    DATABASE_DIR = (ROOT / 'database').resolve()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_PATH = (DATABASE_DIR / 'registrations.db').resolve()
    IS_PERSISTENT_DISK = False

# Unified exception classes
class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class IntegrityError(DatabaseError):
    """Raised on unique constraint or foreign key violations."""
    pass


def sanitize_db_url(url: str) -> str:
    """Masks database credentials for safe diagnostic logging."""
    if not url:
        return "<none>"
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        if '@' in netloc:
            creds, host_port = netloc.split('@', 1)
            user = creds.split(':', 1)[0]
            masked_netloc = f"{user}:***@{host_port}"
        else:
            masked_netloc = netloc
        return urlunparse((parsed.scheme, masked_netloc, parsed.path, '', '', ''))
    except Exception:
        return "<masked_url>"


def get_database_url() -> str | None:
    """
    Returns sanitized PostgreSQL connection string if configured in environment.
    Automatically normalizes postgres:// scheme and routes direct IPv6 Supabase hosts
    through the IPv4 Supavisor connection pooler.
    """
    url = (
        os.environ.get('DATABASE_URL') or 
        os.environ.get('SUPABASE_DB_URL') or 
        os.environ.get('POSTGRES_URL')
    )
    if not url:
        return None
    url = url.strip()
    if not url:
        return None

    # Normalize postgres:// scheme for psycopg2 compatibility
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]

    # Auto-convert Supabase direct URL (IPv6 only) to IPv4 Supavisor connection pooler
    # This prevents [Errno 101] Network is unreachable on Render and IPv4-only hosts
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


def is_postgres(conn=None) -> bool:
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

    def keys(self):
        return super().keys()


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
        try:
            if exc_type is not None:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
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


class SQLiteConnectionWrapper:
    """
    Wraps a sqlite3 connection to ensure proper transaction commit/rollback
    and guaranteed closure when exiting a `with connect() as db:` block.
    """
    is_postgres = False

    def __init__(self, conn):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self._conn.rollback()
            else:
                self._conn.commit()
        finally:
            self._conn.close()

    def cursor(self):
        return self._conn.cursor()

    def execute(self, query, params=None):
        q = query.strip()
        # In Python sqlite3, BEGIN statements are managed automatically; ignore explicit BEGINs
        if q.upper().startswith('BEGIN IMMEDIATE') or q.upper() == 'BEGIN':
            return self
        try:
            if params is None:
                return self._conn.execute(query)
            return self._conn.execute(query, params)
        except sqlite3.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except sqlite3.Error as e:
            raise DatabaseError(str(e)) from e

    def executemany(self, query, seq_of_params):
        try:
            return self._conn.executemany(query, seq_of_params)
        except sqlite3.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except sqlite3.Error as e:
            raise DatabaseError(str(e)) from e

    def executescript(self, script):
        try:
            return self._conn.executescript(script)
        except sqlite3.IntegrityError as e:
            raise IntegrityError(str(e)) from e
        except sqlite3.Error as e:
            raise DatabaseError(str(e)) from e

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, val):
        self._conn.row_factory = val


@contextmanager
def get_db_connection():
    """
    Context manager that yields an active database connection.
    Guarantees that a single authoritative database is used:
    - If PostgreSQL is configured, connects to PostgreSQL or fails safely.
    - If PostgreSQL is NOT configured, connects to SQLite.
    """
    db = connect()
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


def connect():
    """
    Returns an active database connection for direct use.
    Compatible with `with connect() as db:` pattern.
    
    CRITICAL PERSISTENCE RULES:
    1. If DATABASE_URL / SUPABASE_DB_URL is set:
       PostgreSQL is the single authoritative source of truth.
       If connection fails, RAISES DatabaseError immediately (NEVER silently falls back to SQLite).
    2. If DATABASE_URL is NOT set:
       Uses SQLite on the configured persistent path (or local development path).
       Both wrappers guarantee clean commit and connection closure on block exit.
    """
    db_url = get_database_url()
    if db_url:
        if not HAS_PSYCOPG2:
            raise DatabaseError("DATABASE_URL is set in environment, but psycopg2 driver is not installed.")
        try:
            conn = psycopg2.connect(db_url, connect_timeout=15)
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            sanitized = sanitize_db_url(db_url)
            err_msg = f"Authoritative PostgreSQL connection failed to [{sanitized}]: {e}"
            print(f"[CRITICAL DATABASE ERROR] {err_msg}")
            # FAIL SAFELY! Never silently fall back to an ephemeral SQLite database.
            raise DatabaseError(err_msg) from e

    # SQLite connection
    try:
        conn = sqlite3.connect(str(SQLITE_PATH), timeout=15)
        return SQLiteConnectionWrapper(conn)
    except Exception as e:
        err_msg = f"SQLite connection failed to [{SQLITE_PATH}]: {e}"
        print(f"[CRITICAL DATABASE ERROR] {err_msg}")
        raise DatabaseError(err_msg) from e


def init_and_migrate_db():
    """
    Initializes the database schema with safe additive migrations (PostgreSQL or SQLite).
    Idempotent and non-destructive: NEVER deletes, truncates, or resets existing tables or rows.
    """
    with connect() as db:
        if getattr(db, 'is_postgres', False):
            # PostgreSQL Schema
            db.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                team_name TEXT NOT NULL,
                leader_name TEXT,
                track TEXT NOT NULL,
                team_size INTEGER NOT NULL DEFAULT 2,
                devices INTEGER NOT NULL DEFAULT 0,
                transaction_id TEXT UNIQUE,
                proof BYTEA,
                proof_type TEXT,
                status TEXT NOT NULL,
                payment_status TEXT NOT NULL DEFAULT 'PENDING',
                verification_status TEXT NOT NULL DEFAULT 'PENDING_VERIFICATION',
                ticket_status TEXT NOT NULL DEFAULT 'PENDING',
                ticket_token TEXT UNIQUE,
                rejection_reason TEXT,
                fee_amount INTEGER NOT NULL DEFAULT 300,
                member_names TEXT,
                terms_accepted BOOLEAN NOT NULL DEFAULT TRUE,
                internship_accepted BOOLEAN NOT NULL DEFAULT TRUE,
                proof_path TEXT,
                payment_submitted_at TIMESTAMPTZ,
                payment_reviewed_at TIMESTAMPTZ,
                payment_review_notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            db.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                college TEXT,
                role TEXT NOT NULL DEFAULT 'member',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            db.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                admin_user TEXT NOT NULL,
                action TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            db.execute('''
            CREATE TABLE IF NOT EXISTS email_dispatches (
                id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                recipient_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                notification_type TEXT NOT NULL DEFAULT 'FINAL_CONFIRMATION',
                sent_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            db.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            ''')
            db.execute('CREATE INDEX IF NOT EXISTS idx_teams_track ON teams(track);')
            db.execute('CREATE INDEX IF NOT EXISTS idx_members_team_id ON members(team_id);')
            db.execute('CREATE INDEX IF NOT EXISTS idx_admin_actions_team_id ON admin_actions(team_id);')
            db.execute('CREATE INDEX IF NOT EXISTS idx_email_dispatches_team_id ON email_dispatches(team_id);')
            db.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_members_unique_email 
            ON members(email) WHERE email IS NOT NULL AND email != '';
            ''')
            # Additive PostgreSQL migrations
            db.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS proof_path TEXT;")
            db.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS payment_submitted_at TIMESTAMPTZ;")
            db.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS payment_reviewed_at TIMESTAMPTZ;")
            db.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS payment_review_notes TEXT;")
            db.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS rejection_reason TEXT;")
            db.execute("ALTER TABLE members ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'member';")
            db.execute("ALTER TABLE email_dispatches ADD COLUMN IF NOT EXISTS notification_type TEXT DEFAULT 'FINAL_CONFIRMATION';")
            print("[DATABASE INIT] Authoritative PostgreSQL schema initialized successfully.")
            return

        # SQLite Schema
        db.executescript('''
        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            leader_name TEXT,
            track TEXT NOT NULL,
            team_size INTEGER NOT NULL DEFAULT 2,
            devices INTEGER NOT NULL DEFAULT 0,
            transaction_id TEXT UNIQUE,
            proof BLOB,
            proof_type TEXT,
            status TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'PENDING',
            verification_status TEXT NOT NULL DEFAULT 'PENDING_VERIFICATION',
            ticket_status TEXT NOT NULL DEFAULT 'PENDING',
            ticket_token TEXT UNIQUE,
            rejection_reason TEXT,
            fee_amount INTEGER NOT NULL DEFAULT 300,
            member_names TEXT,
            terms_accepted INTEGER NOT NULL DEFAULT 1,
            internship_accepted INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            college TEXT,
            role TEXT DEFAULT 'member',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            admin_user TEXT NOT NULL,
            action TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS email_dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admin_sessions (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_teams_track ON teams(track);
        CREATE INDEX IF NOT EXISTS idx_members_team_id ON members(team_id);
        CREATE INDEX IF NOT EXISTS idx_admin_actions_team_id ON admin_actions(team_id);
        CREATE INDEX IF NOT EXISTS idx_email_dispatches_team_id ON email_dispatches(team_id);
        ''')

        # Additive column migrations for existing teams table
        cur = db.execute("PRAGMA table_info(teams)")
        team_cols = {row['name'] for row in cur.fetchall()}
        if 'payment_status' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN payment_status TEXT DEFAULT 'PENDING'")
        if 'verification_status' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN verification_status TEXT DEFAULT 'PENDING_VERIFICATION'")
        if 'ticket_status' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN ticket_status TEXT DEFAULT 'PENDING'")
        if 'ticket_token' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN ticket_token TEXT")
        if 'rejection_reason' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN rejection_reason TEXT")
        if 'fee_amount' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN fee_amount INTEGER DEFAULT 300")
        if 'updated_at' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
        if 'proof_path' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN proof_path TEXT")
        if 'payment_submitted_at' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN payment_submitted_at TEXT")
        if 'payment_reviewed_at' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN payment_reviewed_at TEXT")
        if 'payment_review_notes' not in team_cols:
            db.execute("ALTER TABLE teams ADD COLUMN payment_review_notes TEXT")

        # Additive column migrations for members table
        cur = db.execute("PRAGMA table_info(members)")
        member_cols = {row['name']: row for row in cur.fetchall()}
        if 'role' not in member_cols:
            db.execute("ALTER TABLE members ADD COLUMN role TEXT DEFAULT 'member'")

        # Additive column migrations for email_dispatches table
        cur = db.execute("PRAGMA table_info(email_dispatches)")
        dispatch_cols = {row['name'] for row in cur.fetchall()}
        if 'notification_type' not in dispatch_cols:
            db.execute("ALTER TABLE email_dispatches ADD COLUMN notification_type TEXT DEFAULT 'FINAL_CONFIRMATION'")

        # Create unique partial index on member email
        db.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_members_unique_email 
        ON members(email) WHERE email IS NOT NULL AND email != ''
        ''')
        print(f"[DATABASE INIT] SQLite schema initialized at {SQLITE_PATH}")


def get_database_diagnostics() -> dict:
    """
    Inspects the active database and returns a sanitized diagnostic summary
    for telemetry, startup logs, and admin system health monitoring.
    Never exposes passwords, keys, or private participant information.
    """
    is_render = bool(os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'))
    db_url = get_database_url()

    if db_url and HAS_PSYCOPG2:
        engine = 'postgresql'
        sanitized_endpoint = sanitize_db_url(db_url)
        persistence_tier = 'SECURE_POSTGRESQL'
        is_persistent = True
    elif IS_PERSISTENT_DISK:
        engine = 'sqlite'
        sanitized_endpoint = str(SQLITE_PATH)
        persistence_tier = 'SECURE_PERSISTENT_DISK'
        is_persistent = True
    elif is_render:
        engine = 'sqlite'
        sanitized_endpoint = str(SQLITE_PATH)
        persistence_tier = 'UNSAFE_EPHEMERAL_CONTAINER'
        is_persistent = False
    else:
        engine = 'sqlite'
        sanitized_endpoint = str(SQLITE_PATH)
        persistence_tier = 'LOCAL_DEVELOPMENT'
        is_persistent = True

    # Count active records
    teams_count = 0
    members_count = 0
    verified_count = 0
    paid_count = 0
    conn_error = None

    try:
        with connect() as db:
            row_t = db.execute('SELECT COUNT(*) FROM teams').fetchone()
            teams_count = row_t[0] if row_t else 0
            row_m = db.execute('SELECT COUNT(*) FROM members').fetchone()
            members_count = row_m[0] if row_m else 0
            row_v = db.execute("SELECT COUNT(*) FROM teams WHERE verification_status = 'VERIFIED'").fetchone()
            verified_count = row_v[0] if row_v else 0
            row_p = db.execute("SELECT COUNT(*) FROM teams WHERE payment_status = 'PAID'").fetchone()
            paid_count = row_p[0] if row_p else 0
    except Exception as e:
        conn_error = str(e)

    supa_url, supa_key = get_supabase_credentials()
    storage_type = 'supabase_storage' if (supa_url and supa_key) else 'local_disk'

    return {
        'engine': engine,
        'persistence_tier': persistence_tier,
        'is_persistent': is_persistent,
        'sanitized_endpoint': sanitized_endpoint,
        'is_render': is_render,
        'teams_count': teams_count,
        'members_count': members_count,
        'verified_count': verified_count,
        'paid_count': paid_count,
        'storage_type': storage_type,
        'driver': 'psycopg2' if engine == 'postgresql' else 'sqlite3',
        'connection_error': conn_error
    }


def sync_sqlite_to_postgres(sqlite_path: str = None) -> dict:
    """
    Safely and idempotently reconciles registrations from a local SQLite database
    into the active PostgreSQL database.
    Uses ON CONFLICT (id) DO NOTHING so existing PostgreSQL data is never overwritten.
    """
    db_url = get_database_url()
    if not db_url or not HAS_PSYCOPG2:
        return {'status': 'SKIPPED', 'reason': 'PostgreSQL DATABASE_URL not configured.'}

    src_path = Path(sqlite_path or SQLITE_PATH)
    if not src_path.is_file():
        return {'status': 'SKIPPED', 'reason': f'Source SQLite file {src_path} not found.'}

    src_conn = sqlite3.connect(str(src_path))
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    teams_synced = 0
    members_synced = 0

    try:
        pg_conn = psycopg2.connect(db_url, connect_timeout=15)
        pg_cur = pg_conn.cursor()

        # Sync teams
        src_teams = src_cur.execute('SELECT * FROM teams').fetchall()
        for t in src_teams:
            cols = list(t.keys())
            vals = [t[c] for c in cols]
            col_names = ', '.join(cols)
            placeholders = ', '.join(['%s'] * len(cols))
            query = f'''
                INSERT INTO teams ({col_names})
                VALUES ({placeholders})
                ON CONFLICT (id) DO NOTHING
            '''
            pg_cur.execute(query, vals)
            if pg_cur.rowcount > 0:
                teams_synced += 1

        # Sync members
        src_members = src_cur.execute('SELECT team_id, name, email, phone, college, role FROM members').fetchall()
        for m in src_members:
            # Check if member exists for this team
            pg_cur.execute('''
                SELECT id FROM members 
                WHERE team_id = %s AND name = %s
            ''', (m['team_id'], m['name']))
            if not pg_cur.fetchone():
                pg_cur.execute('''
                    INSERT INTO members (team_id, name, email, phone, college, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (m['team_id'], m['name'], m['email'], m['phone'], m['college'], m['role']))
                members_synced += 1

        pg_conn.commit()
        pg_cur.close()
        pg_conn.close()
        src_conn.close()

        return {
            'status': 'SUCCESS',
            'teams_synced': teams_synced,
            'members_synced': members_synced,
            'total_src_teams': len(src_teams)
        }
    except Exception as e:
        src_conn.close()
        return {'status': 'ERROR', 'error': str(e)}


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
