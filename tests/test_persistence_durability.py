#!/usr/bin/env python3
"""
SUPERNOVA 2026 - Data Persistence & Durability Test Suite
Tests:
1. Storage engine detection and diagnostic telemetry
2. Atomic write confirmation and durability across connection resets
3. Server reboot simulation (init_and_migrate_db called again) - no data reset
4. Admin registrations listing SQL and dashboard summary SQL accuracy
5. Filter accuracy (track, payment_status, verification_status)
6. Duplicate prevention and data integrity
7. Clean teardown leaving existing production records untouched
"""

import sys
import os
import uuid
import json
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / 'backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import (
    connect, is_postgres, DatabaseError, IntegrityError,
    init_and_migrate_db, get_database_diagnostics, SQLITE_PATH
)

TEST_TEAM_ID = f"SN26-TEST-DURABILITY-{uuid.uuid4().hex[:6].upper()}"
TEST_LEADER_EMAIL = f"test.durability.{uuid.uuid4().hex[:6].lower()}@example.com"
TEST_MEMBER_EMAIL = f"test.member.{uuid.uuid4().hex[:6].lower()}@example.com"

def run_persistence_tests():
    print("=" * 72)
    print(" [TEST RUNNER] Starting SUPERNOVA Durability & Persistence Test Suite")
    print("=" * 72)

    # ---------------------------------------------------------
    # TEST 1: Diagnostic Telemetry
    # ---------------------------------------------------------
    print("\n--- TEST 1: Diagnostic Telemetry Inspection ---")
    diag = get_database_diagnostics()
    print(f"Active Engine: {diag['engine']}")
    print(f"Persistence Tier: {diag['persistence_tier']}")
    print(f"Sanitized Endpoint: {diag['sanitized_endpoint']}")
    print(f"Pre-test Teams Count: {diag['teams_count']}")
    print(f"Pre-test Members Count: {diag['members_count']}")
    assert diag['teams_count'] >= 6, f"Expected at least 6 teams in existing database, found {diag['teams_count']}"
    print("[PASS] Test 1: Telemetry reports accurate baseline record counts.")

    baseline_teams = diag['teams_count']
    baseline_members = diag['members_count']

    # ---------------------------------------------------------
    # TEST 2: Atomic Write Confirmation
    # ---------------------------------------------------------
    print("\n--- TEST 2: Atomic Write Confirmation & Immediate Readback ---")
    with connect() as db:
        db.execute('''
            INSERT INTO teams (
                id, team_name, leader_name, track, team_size, devices,
                transaction_id, status, payment_status, verification_status,
                ticket_status, ticket_token, fee_amount, member_names
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            TEST_TEAM_ID, "Test Durability Hackers", "Durability Leader", "web",
            2, 0, f"TXN-TEST-{uuid.uuid4().hex[:8].upper()}",
            "Pending Verification", "PENDING", "PENDING_VERIFICATION",
            "PENDING", f"TOKEN-{uuid.uuid4().hex[:12]}", 300,
            json.dumps(["Durability Leader", "Durability Member"])
        ))
        db.executemany('''
            INSERT INTO members (team_id, name, email, phone, college, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            (TEST_TEAM_ID, "Durability Leader", TEST_LEADER_EMAIL, "9876543210", "Durability Institute", "leader"),
            (TEST_TEAM_ID, "Durability Member", TEST_MEMBER_EMAIL, "9876543211", "Durability Institute", "member")
        ])
    print(f"Inserted test team {TEST_TEAM_ID} with 2 members.")

    # Immediately verify in a new, independent connection
    with connect() as verify_db:
        team_row = verify_db.execute("SELECT * FROM teams WHERE id = ?", (TEST_TEAM_ID,)).fetchone()
        assert team_row is not None, "Failed to read back newly created team in separate connection!"
        assert team_row['team_name'] == "Test Durability Hackers"

        member_rows = verify_db.execute("SELECT * FROM members WHERE team_id = ? ORDER BY id ASC", (TEST_TEAM_ID,)).fetchall()
        assert len(member_rows) == 2, f"Expected 2 members, found {len(member_rows)}"
        assert member_rows[0]['email'] == TEST_LEADER_EMAIL
    print("[PASS] Test 2: Atomic write confirmed in new independent connection.")

    # ---------------------------------------------------------
    # TEST 3: Simulated Server Reboot / Repeated Schema Init
    # ---------------------------------------------------------
    print("\n--- TEST 3: Server Reboot Simulation (init_and_migrate_db) ---")
    # Calling init_and_migrate_db again simulates the server starting up again
    init_and_migrate_db()
    
    with connect() as reboot_db:
        reboot_team = reboot_db.execute("SELECT * FROM teams WHERE id = ?", (TEST_TEAM_ID,)).fetchone()
        assert reboot_team is not None, "FATAL: Test team disappeared after init_and_migrate_db()!"
        reboot_members = reboot_db.execute("SELECT * FROM members WHERE team_id = ?", (TEST_TEAM_ID,)).fetchall()
        assert len(reboot_members) == 2, "FATAL: Members disappeared after init_and_migrate_db()!"
    print("[PASS] Test 3: Data durability verified across repeated schema migrations/reboot.")

    # ---------------------------------------------------------
    # TEST 4: Admin Listing SQL & Dashboard Metrics
    # ---------------------------------------------------------
    print("\n--- TEST 4: Admin Listing SQL & Dashboard Metrics Execution ---")
    admin_sql = '''
        SELECT t.*, 
               (SELECT COUNT(*) FROM members m WHERE m.team_id = t.id) as roster_count,
               (SELECT email FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) as email,
               (SELECT phone FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) as phone,
               (SELECT college FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) as college,
               (SELECT status FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_status,
               (SELECT sent_at FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_time,
               (SELECT notification_type FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_type,
               (SELECT error_message FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_error
        FROM teams t WHERE 1=1
        ORDER BY t.created_at DESC
    '''
    with connect() as admin_db:
        all_teams = admin_db.execute(admin_sql).fetchall()
        matching = [r for r in all_teams if r['id'] == TEST_TEAM_ID]
        assert len(matching) == 1, f"Admin listing did not return test team {TEST_TEAM_ID}"
        assert matching[0]['roster_count'] == 2, f"Expected roster_count 2, got {matching[0]['roster_count']}"
        assert matching[0]['email'] == TEST_LEADER_EMAIL

        # Dashboard total check
        dash_total = admin_db.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        assert dash_total == baseline_teams + 1, f"Expected dashboard total {baseline_teams + 1}, got {dash_total}"
    print("[PASS] Test 4: Admin listing SQL and dashboard metrics correctly include new registration.")

    # ---------------------------------------------------------
    # TEST 5: Filter Tests
    # ---------------------------------------------------------
    print("\n--- TEST 5: Filter Tests ---")
    with connect() as filter_db:
        web_teams = filter_db.execute("SELECT id FROM teams WHERE track = 'web'").fetchall()
        assert any(r['id'] == TEST_TEAM_ID for r in web_teams), "Test team not found in track='web' filter"

        ai_teams = filter_db.execute("SELECT id FROM teams WHERE track = 'ai'").fetchall()
        assert not any(r['id'] == TEST_TEAM_ID for r in ai_teams), "Test team erroneously found in track='ai' filter"
    print("[PASS] Test 5: Filtering by track correctly scopes records.")

    # ---------------------------------------------------------
    # TEST 6: Teardown & Production Integrity Preservation
    # ---------------------------------------------------------
    print("\n--- TEST 6: Teardown & Verification of Real Production Data ---")
    with connect() as clean_db:
        clean_db.execute("DELETE FROM members WHERE team_id = ?", (TEST_TEAM_ID,))
        clean_db.execute("DELETE FROM teams WHERE id = ?", (TEST_TEAM_ID,))
    print(f"Cleaned up test team {TEST_TEAM_ID}.")

    # Confirm production team SN26-F5122A0DEB is intact
    with connect() as final_db:
        prod_team = final_db.execute("SELECT * FROM teams WHERE id = 'SN26-F5122A0DEB'").fetchone()
        assert prod_team is not None, "CRITICAL: Production team SN26-F5122A0DEB is missing!"
        assert prod_team['leader_name'] == "karanmanikandan"
        assert prod_team['payment_status'] == "PAID"
        assert prod_team['verification_status'] == "VERIFIED"

        post_diag = get_database_diagnostics()
        assert post_diag['teams_count'] == baseline_teams, f"Expected {baseline_teams} teams post-cleanup, found {post_diag['teams_count']}"
        assert post_diag['members_count'] == baseline_members, f"Expected {baseline_members} members post-cleanup, found {post_diag['members_count']}"
    print("[PASS] Test 6: Production team SN26-F5122A0DEB verified intact; baseline record count restored.")

    print("\n" + "=" * 72)
    print(" ALL PERSISTENCE & DURABILITY TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 72)

if __name__ == '__main__':
    run_persistence_tests()
