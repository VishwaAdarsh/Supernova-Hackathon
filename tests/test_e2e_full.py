import base64
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))

from backend.server import Server, ThreadingHTTPServer, connect, resolve_public_base_url

TEST_PORT = 8999
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def run_server():
    server = ThreadingHTTPServer(('127.0.0.1', TEST_PORT), Server)
    server.serve_forever()

def http_json(path, method='GET', data=None, headers=None):
    h = headers.copy() if headers else {}
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8')
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {'raw': raw}

def http_raw(path, method='GET', headers=None):
    h = headers.copy() if headers else {}
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()

def main():
    print("=== STARTING SUPERNOVA 2026 E2E SUITE ===")
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1) # wait for server to start

    # 1. Track availability check
    print("\n[1] Testing GET /api/registrations (Track availability)...")
    status, data = http_json("/api/registrations")
    assert status == 200, f"Expected 200, got {status}"
    assert "web" in data and "ai" in data, "Tracks missing"
    print(f"Track Availability: Web={data['web']['claimed']}/{data['web']['total']}, AI={data['ai']['claimed']}/{data['ai']['total']}")

    # Clean up any leftover test teams
    test_ts = int(time.time())
    with connect() as conn:
        conn.execute("DELETE FROM members WHERE email LIKE 'e2e.%@example.com'")
        conn.execute("DELETE FROM teams WHERE leader_name = 'E2E Lead'")

    # 2. Registration Submission
    print("\n[2] Testing POST /api/registrations (Team Registration)...")
    team_payload = {
        "team_name": f"E2E Test Team {test_ts}",
        "leader_name": "E2E Lead",
        "email": f"e2e.lead.{test_ts}@example.com",
        "phone": "9876543210",
        "college": "Tolani College of Commerce",
        "track": "web",
        "team_size": 2,
        "members": [
            {"name": "E2E Member Two", "email": f"e2e.mem2.{test_ts}@example.com", "phone": "9876543211", "college": "Tolani College of Commerce"}
        ],
        "terms_accepted": True,
        "internship_accepted": True
    }
    status, res = http_json("/api/registrations", method="POST", data=team_payload)
    assert status == 201, f"Expected 201 Created, got {status}: {res}"
    team_id = res['id']
    ticket_token = res['ticket_token']
    print(f"Registration Created: ID={team_id}, TicketToken={ticket_token}")

    # 3. Lookup Ticket
    print("\n[3] Testing GET /api/ticket/<ref>...")
    status, tkt = http_json(f"/api/ticket/{team_id}")
    assert status == 200, f"Expected 200, got {status}"
    assert tkt['payment_status'] == 'PENDING'
    assert tkt['verification_status'] == 'PENDING_VERIFICATION'
    assert tkt['ticket_status'] == 'PENDING'
    print(f"Ticket Status verified: {tkt['ticket_status']}, Payment: {tkt['payment_status']}")

    # 4. Upload Payment Proof
    print("\n[4] Testing POST /api/registrations/<id>/payment-proof...")
    # 1x1 transparent PNG as test proof
    dummy_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    proof_payload = {
        "proof_base64": f"data:image/png;base64,{dummy_png}",
        "transaction_id": f"TXN-E2E-{int(time.time())}"
    }
    status, p_res = http_json(f"/api/registrations/{team_id}/payment-proof", method="POST", data=proof_payload)
    assert status == 200, f"Expected 200, got {status}: {p_res}"
    print(f"Proof Upload Response: {p_res.get('message')}")

    # 5. Admin Flow
    print("\n[5] Testing Admin Authentication & Review Workflow...")
    admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'supernova2026#admin')
    status, login_res = http_json("/api/admin/login", method="POST", data={"username": admin_user, "password": admin_pass})
    assert status == 200, f"Admin login failed: {login_res}"
    admin_token = login_res['token']
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("Admin login successful!")

    # Verify registration in admin list
    status, admin_resp = http_json(f"/api/admin/registrations?search={team_id}", headers=admin_headers)
    assert status == 200
    admin_teams = admin_resp['registrations']
    assert len(admin_teams) >= 1
    admin_team = admin_teams[0]
    assert admin_team['id'] == team_id
    assert admin_team['has_proof'] is True
    print(f"Admin found team in registrations list with has_proof={admin_team['has_proof']}")

    # Admin Approve Payment
    print("\n[6] Admin Approves Payment...")
    status, ver_res = http_json(
        f"/api/admin/registrations/{team_id}/verify-payment",
        method="POST",
        data={"action": "VERIFY", "notes": "E2E Verified OK"},
        headers=admin_headers
    )
    assert status == 200, f"Failed to verify payment: {ver_res}"
    print("Payment Verified by Admin!")

    # Admin Approve Team
    print("\n[7] Admin Approves Team Registration...")
    status, app_res = http_json(
        f"/api/admin/registrations/{team_id}/approve",
        method="POST",
        data={"action": "APPROVE", "notes": "E2E Final Approval"},
        headers=admin_headers
    )
    assert status == 200, f"Failed to approve team: {app_res}"
    print("Team Approved by Admin!")

    # 8. Download Final Pass PDF
    print("\n[8] Testing Download Final PDF Pass (/api/ticket/<id>/pass.pdf)...")
    status, headers, pdf_data = http_raw(f"/api/ticket/{team_id}/pass.pdf")
    assert status == 200, f"Expected 200, got {status}"
    assert headers.get('Content-Type') == 'application/pdf', f"Unexpected Content-Type: {headers.get('Content-Type')}"
    assert pdf_data.startswith(b'%PDF'), "PDF output missing %PDF magic bytes"
    assert len(pdf_data) > 10000, f"PDF file size suspiciously small: {len(pdf_data)}"
    print(f"Official Vector PDF Pass generated successfully! Size: {len(pdf_data)} bytes")

    # 9. Clean up test record from database
    print("\n[9] Cleaning up test records...")
    with connect() as conn:
        conn.execute("DELETE FROM members WHERE team_id = ?", (team_id,))
        conn.execute("DELETE FROM admin_actions WHERE team_id = ?", (team_id,))
        conn.execute("DELETE FROM email_dispatches WHERE team_id = ?", (team_id,))
        conn.execute("DELETE FROM teams WHERE id = ?", (team_id,))
    print("Clean up complete.")

    print("\n==========================================")
    print("   ALL E2E INTEGRATION TESTS PASSED 100%!  ")
    print("==========================================")

if __name__ == '__main__':
    main()
