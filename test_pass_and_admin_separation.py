# test_pass_and_admin_separation.py - Verification suite for Supernova Pass & Admin Separation
import urllib.request
import urllib.error
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def get(path, headers=None):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {})
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

def get_html(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as res:
        return res.status, res.read().decode('utf-8')

def post(path, data, headers=None):
    h = {'Content-Type': 'application/json'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=json.dumps(data).encode('utf-8'), headers=h)
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

def post_err(path, data, headers=None):
    h = {'Content-Type': 'application/json'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=json.dumps(data).encode('utf-8'), headers=h)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

print("=== STARTING SUPERNOVA PASS & ADMIN SEPARATION TESTS ===")

# Test 1: Verify public index.html has NO admin dashboard embedded
status, index_html = get_html("/")
assert status == 200
assert 'id="stateAdminContainer"' not in index_html, "Found stateAdminContainer in public index.html!"
assert 'handleAdminLogin' not in index_html, "Found handleAdminLogin in public index.html!"
assert '04 ADMIN' not in index_html, "Found 04 ADMIN tab in public index.html!"
assert 'href="/admin"' in index_html, "Admin link missing in footer!"
print("[PASS] 1. Public page (index.html) is completely free of admin UI/forms/tabs")

# Test 2: Verify dedicated /admin route serves admin.html and protects admin endpoints
status, admin_html = get_html("/admin")
assert status == 200
assert "SUPERNOVA 2026 // Admin Telemetry Command Center" in admin_html
assert "COMMAND AUTHENTICATION" in admin_html

# Unauthenticated admin API call rejected
status, unauth = post_err("/api/admin/registrations", {})
assert status == 401 or status == 404
print("[PASS] 2. Dedicated /admin serves admin.html and server protects admin API")

# Test 3: Authenticate admin
status, auth_data = post("/api/admin/login", {"username": "admin", "password": "supernova2026#admin"})
assert status == 200 and "token" in auth_data
admin_token = auth_data["token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
print("[PASS] 3. Admin successfully authenticated with session token")

# Test 4: Register a new team (Initial State: Payment=PENDING, Verification=PENDING)
uid = uuid.uuid4().hex[:6]
reg_payload = {
    "leader_name": "Valeria Richards",
    "email": f"valeria.{uid}@quantum.edu",
    "phone": "9876543100",
    "college": "Tolani College of Commerce & Science",
    "track": "web",
    "team_size": 2,
    "members": [{"name": "Franklin Richards", "email": f"franklin.{uid}@quantum.edu", "phone": "9876543101", "college": "Tolani College"}],
    "terms_accepted": True
}
status, reg_res = post("/api/registrations", reg_payload)
assert status == 201
team_id = reg_res["id"]
print(f"[PASS] 4. Team registered: {team_id}")

# Test 5: Verify Pending Payment + Pending Approval CANNOT access official ticket
status, tick_pending = get(f"/api/ticket/{team_id}")
assert status == 200
assert tick_pending["is_eligible"] is False, "Pending team should NOT be eligible!"
assert tick_pending["ticket_token"] is None, "Pending team should NOT have ticket_token!"
assert tick_pending["ticket_status"] == "PENDING"
assert "payment verification and organizer approval pending" in tick_pending["status_message"].lower()
print("[PASS] 5. Pending payment + approval strictly denies ticket access (is_eligible=False, token=None)")

# Test 6: Verify Payment ONLY (Payment=PAID, Verification=PENDING) CANNOT access official ticket
status, pay_res = post(f"/api/admin/registrations/{team_id}/verify-payment", {}, headers=admin_headers)
assert status == 200 and pay_res["payment_status"] == "PAID"

status, tick_paid_only = get(f"/api/ticket/{team_id}")
assert tick_paid_only["payment_status"] == "PAID"
assert tick_paid_only["verification_status"] != "VERIFIED"
assert tick_paid_only["is_eligible"] is False, "Paid-only team should NOT be eligible without approval!"
assert tick_paid_only["ticket_token"] is None, "Paid-only team should NOT receive ticket_token!"
print("[PASS] 6. Verified payment without approval strictly denies ticket access (is_eligible=False, token=None)")

# Test 7: Approve Team (Now BOTH Payment=PAID and Verification=VERIFIED) -> Unlocks Official Ticket!
status, app_res = post(f"/api/admin/registrations/{team_id}/approve", {}, headers=admin_headers)
assert status == 200 and app_res["ticket_status"] == "CONFIRMED"

status, tick_confirmed = get(f"/api/ticket/{team_id}")
assert tick_confirmed["payment_status"] == "PAID"
assert tick_confirmed["verification_status"] == "VERIFIED"
assert tick_confirmed["is_eligible"] is True, "Confirmed team MUST be eligible!"
assert tick_confirmed["ticket_status"] == "CONFIRMED"
assert tick_confirmed["ticket_token"] is not None and len(tick_confirmed["ticket_token"]) > 10
assert "officially registered" in tick_confirmed["status_message"].lower()
print(f"[PASS] 7. Both conditions satisfied: Official ticket pass UNLOCKED with token: {tick_confirmed['ticket_token'][:12]}...")

# Test 8: Public /verify route is removed (404), consolidated into /admin
try:
    status, _ = get_html(f"/verify?id={team_id}")
    assert False, "Expected 404 for /verify"
except urllib.error.HTTPError as e:
    assert e.code == 404
print(f"[PASS] 8. Separate /verify route removed (404 Not Found), consolidated into /admin")

# Test 9: Rejection workflow verification
uid2 = uuid.uuid4().hex[:6]
rej_payload = {
    "leader_name": "Victor Von Doom",
    "email": f"doom.{uid2}@quantum.edu",
    "phone": "9876543109",
    "college": "Latveria Institute",
    "track": "aiml",
    "team_size": 2,
    "members": [{"name": "Boris", "email": f"boris.{uid2}@quantum.edu", "phone": "9876543108"}],
    "terms_accepted": True
}
status, rej_team = post("/api/registrations", rej_payload)
rej_id = rej_team["id"]

status, rej_action = post(f"/api/admin/registrations/{rej_id}/reject", {"reason": "Non-accredited institution"}, headers=admin_headers)
assert status == 200 and rej_action["verification_status"] == "REJECTED"

status, tick_rejected = get(f"/api/ticket/{rej_id}")
assert tick_rejected["is_eligible"] is False
assert tick_rejected["verification_status"] == "REJECTED"
assert tick_rejected["rejection_reason"] == "Non-accredited institution"
assert tick_rejected["ticket_token"] is None
print(f"[PASS] 9. Rejection with mandatory reason strictly revokes pass eligibility")

# Test 10: Verify print and download elements exist in index.html
assert 'id="officialTicketPass"' in index_html
assert 'downloadPassPNG()' in index_html
assert 'downloadPassPDF()' in index_html
assert 'printPass()' in index_html
assert '@media print' in index_html
print("[PASS] 10. PNG, PDF, and dedicated @media print pass export verified")

print("\n>>> ALL 10 SUPERNOVA VERIFICATION TESTS PASSED PERFECTLY! <<<")
