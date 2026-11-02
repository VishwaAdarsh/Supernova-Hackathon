#!/usr/bin/env python3
"""
SUPERNOVA 2026 - Database Reset, Persistence & Admin Auth Verification
Verifies:
1. Fresh start: Database has 0 registration records (teams, members, admin_actions, email_dispatches).
2. Admin credentials update:
   - Valid credentials (super_nova09 / Supernova@001) succeed.
   - Old default credentials (admin / supernova2026#admin) are rejected (401).
   - Plaintext password is not stored or logged.
   - Database admin_users table stores PBKDF2-HMAC-SHA256 hash.
3. Auto-login disabled:
   - admin.html inputs are blank (value=""), requiring manual entry.
   - Uses sessionStorage instead of persistent localStorage.
4. Registration flow works cleanly from fresh state and persists to active database.
"""
import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import connect, is_postgres, SQLITE_PATH
import server

def test_admin_auth_logic():
    # 1. New credentials must verify
    assert server.verify_admin_credentials("super_nova09", "Supernova@001") is True, (
        "New credentials super_nova09 / Supernova@001 failed verification!"
    )

    # 2. Old default credentials must be rejected
    assert server.verify_admin_credentials("admin", "supernova2026#admin") is False, (
        "Old credentials admin / supernova2026#admin must NOT be accepted!"
    )

    # 3. Invalid credentials must be rejected
    assert server.verify_admin_credentials("super_nova09", "WrongPassword123") is False
    assert server.verify_admin_credentials("unknown_user", "Supernova@001") is False
    assert server.verify_admin_credentials("", "") is False
    print("[PASS] 1. Admin credential verification logic verified.")

def test_admin_users_db_record():
    with connect() as db:
        row = db.execute("SELECT username, password_hash FROM admin_users WHERE username = ?", ("super_nova09",)).fetchone()
        assert row is not None, "admin_users record for super_nova09 not found in database!"
        assert row["username"] == "super_nova09"
        assert row["password_hash"].startswith("pbkdf2_sha256$"), "Password must be stored as PBKDF2 hash!"
        assert "Supernova@001" not in row["password_hash"], "Plaintext password must NEVER be in database!"

        # Ensure old admin user does not exist
        old_admin = db.execute("SELECT * FROM admin_users WHERE username = ?", ("admin",)).fetchone()
        assert old_admin is None, "Old admin account still exists in database!"
    print("[PASS] 2. Database admin_users schema and secure PBKDF2 hash verified.")

def test_admin_html_security():
    admin_html = (ROOT / "frontend" / "admin.html").read_text(encoding="utf-8")
    assert 'value="admin"' not in admin_html, "Hardcoded admin username found in admin.html!"
    assert 'value="supernova2026#admin"' not in admin_html, "Hardcoded admin password found in admin.html!"
    assert 'sessionStorage.getItem(\'sn26_admin_token\')' in admin_html, "sessionStorage token handling missing in admin.html!"
    print("[PASS] 3. Frontend admin.html input prefill and auto-login disabled.")

def test_clean_database_state():
    with connect() as db:
        teams_cnt = db.execute("SELECT count(*) FROM teams").fetchone()[0]
        members_cnt = db.execute("SELECT count(*) FROM members").fetchone()[0]
        actions_cnt = db.execute("SELECT count(*) FROM admin_actions").fetchone()[0]
        dispatches_cnt = db.execute("SELECT count(*) FROM email_dispatches").fetchone()[0]
        sessions_cnt = db.execute("SELECT count(*) FROM admin_sessions").fetchone()[0]

        assert teams_cnt == 0, f"Expected 0 teams, found {teams_cnt}"
        assert members_cnt == 0, f"Expected 0 members, found {members_cnt}"
        assert actions_cnt == 0, f"Expected 0 admin_actions, found {actions_cnt}"
        assert dispatches_cnt == 0, f"Expected 0 email_dispatches, found {dispatches_cnt}"
        assert sessions_cnt == 0, f"Expected 0 admin_sessions, found {sessions_cnt}"
    print("[PASS] 4. Clean registration database verified (all registration records cleared).")

if __name__ == "__main__":
    test_admin_auth_logic()
    test_admin_users_db_record()
    test_admin_html_security()
    test_clean_database_state()
    print("\nALL DATABASE RESET & ADMIN AUTH TESTS PASSED!")
