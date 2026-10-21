import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
# test_integration.py - Full E2E Integration Suite for Supernova 2026 Registration
import urllib.request
import urllib.error
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def get(path, headers=None):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {})
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode('utf-8'))

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

print("=== RUNNING SUPERNOVA 2026 INTEGRATION TEST SUITE ===")

# Test 1: Track availability
status, data = get("/api/registrations")
assert status == 200, f"Expected 200, got {status}"
assert "web" in data and "ai" in data
print("[PASS] 1. Live track availability endpoint")

# Test 2: Solo registration rejected
solo_payload = {
    "leader_name": "Solo Hacker",
    "email": f"solo.{uuid.uuid4().hex[:6]}@quantum.edu",
    "phone": "9876543210",
    "college": "Tolani College",
    "track": "web",
    "team_size": 1,
    "members": [],
    "terms_accepted": True
}
status, err_data = post_err("/api/registrations", solo_payload)
assert status == 400, f"Expected 400 for Solo, got {status}"
print("[PASS] 2. Solo team size strictly rejected (400)")

# Test 3: Duo registration succeeds
u = uuid.uuid4().hex[:6]
duo_payload = {
    "leader_name": "Ada Lovelace",
    "email": f"ada.{u}@quantum.edu",
    "phone": "9876543201",
    "college": "Tolani College of Commerce & Science",
    "track": "web",
    "team_size": 2,
    "members": [{"name": "Charles Babbage", "email": f"charles.{u}@quantum.edu", "phone": "9876543202", "college": "Tolani College"}],
    "terms_accepted": True
}
status, duo_data = post("/api/registrations", duo_payload)
assert status == 201, f"Expected 201, got {status}"
duo_id = duo_data["id"]
assert duo_data["team_size"] == 2
assert duo_data["fee_amount"] == 300
assert duo_data["payment_status"] == "PENDING"
assert duo_data["ticket_status"] == "PENDING"
print(f"[PASS] 3. Duo team registered successfully (ID: {duo_id}, Fee: INR 300, Status: PENDING)")

# Test 4: Trio registration succeeds
u2 = uuid.uuid4().hex[:6]
trio_payload = {
    "leader_name": "Alan Turing",
    "email": f"alan.{u2}@quantum.edu",
    "phone": "9876543203",
    "college": "Tolani College of Commerce & Science",
    "track": "aiml",
    "team_size": 3,
    "members": [
        {"name": "Joan Clarke", "email": f"joan.{u2}@quantum.edu", "phone": "9876543204", "college": "Tolani College"},
        {"name": "Hugh Alexander", "email": f"hugh.{u2}@quantum.edu", "phone": "9876543205", "college": "Tolani College"}
    ],
    "terms_accepted": True
}
status, trio_data = post("/api/registrations", trio_payload)
assert status == 201, f"Expected 201, got {status}"
trio_id = trio_data["id"]
assert trio_data["team_size"] == 3
assert trio_data["fee_amount"] == 300
print(f"[PASS] 4. Trio team registered successfully (ID: {trio_id}, Fee: INR 300, Status: PENDING)")

# Test 5: Duplicate email rejection
duplicate_payload = {
    "leader_name": "Impostor Lead",
    "email": duo_payload["email"], # already registered
    "phone": "9876543299",
    "college": "Another College",
    "track": "web",
    "team_size": 2,
    "members": [{"name": "Partner", "email": f"unique.{uuid.uuid4().hex[:6]}@quantum.edu", "phone": "9876543298"}],
    "terms_accepted": True
}
status, dup_err = post_err("/api/registrations", duplicate_payload)
assert status == 409, f"Expected 409 for duplicate email, got {status}"
print("[PASS] 5. Duplicate operative email strictly rejected (409)")

# Test 6: Ticket endpoint returns pending pass
status, tick = get(f"/api/ticket/{duo_id}")
assert status == 200, f"Expected 200, got {status}"
assert tick["id"] == duo_id
assert tick["payment_status"] == "PENDING"
assert tick["ticket_status"] == "PENDING"
assert tick["fee_amount"] == 300
assert tick["ticket_token"] is None # token is only revealed when CONFIRMED
print(f"[PASS] 6. Ticket endpoint returns PENDING status initially without premature token")

# Test 7: Admin authentication
status, wrong_auth = post_err("/api/admin/login", {"username": "admin", "password": "wrongpassword"})
assert status == 401, f"Expected 401, got {status}"

status, auth = post("/api/admin/login", {"username": "admin", "password": "supernova2026#admin"})
assert status == 200 and "token" in auth
admin_token = auth["token"]
print("[PASS] 7. Admin authentication gates secured (Invalid=401, Valid=200 Bearer Token)")

admin_headers = {"Authorization": f"Bearer {admin_token}"}

# Test 8: Admin dashboard telemetry
status, dash = get("/api/admin/dashboard", headers=admin_headers)
assert status == 200
assert dash["summary"]["total_teams"] >= 2
print(f"[PASS] 8. Admin dashboard telemetry live: {dash['summary']['total_teams']} teams total")

# Test 9: Admin record payment
status, pay_res = post(f"/api/admin/registrations/{duo_id}/verify-payment", {}, headers=admin_headers)
assert status == 200 and pay_res["payment_status"] == "PAID"
print(f"[PASS] 9. Admin recorded on-site payment for {duo_id} (Status: PAID)")

# Test 10: Admin approve team & issue pass
status, app_res = post(f"/api/admin/registrations/{duo_id}/approve", {}, headers=admin_headers)
assert status == 200 and app_res["ticket_status"] == "CONFIRMED"
assert "email_dispatch" in app_res
print(f"[PASS] 10. Admin approved team & issued ticket pass (Email Dispatch: {app_res['email_dispatch']['status']})")

# Test 11: Ticket endpoint now returns CONFIRMED status and cryptographic token
status, confirmed_tick = get(f"/api/ticket/{duo_id}")
assert status == 200
assert confirmed_tick["ticket_status"] == "CONFIRMED"
assert confirmed_tick["payment_status"] == "PAID"
assert confirmed_tick["ticket_token"] is not None and len(confirmed_tick["ticket_token"]) > 10
print(f"[PASS] 11. Ticket Pass updated to CONFIRMED with cryptographic token: {confirmed_tick['ticket_token'][:12]}...")

# Test 12: Admin resend email
status, resend_res = post(f"/api/admin/registrations/{duo_id}/resend-email", {}, headers=admin_headers)
assert status == 200 and "dispatch" in resend_res
print(f"[PASS] 12. Admin resend email workflow verified (Status: {resend_res['dispatch']['status']})")

# Test 13: Admin reject team with mandatory reason
status, rej_res = post(f"/api/admin/registrations/{trio_id}/reject", {"reason": "Duplicate college registration anomaly"}, headers=admin_headers)
assert status == 200 and rej_res["verification_status"] == "REJECTED"

status, rejected_tick = get(f"/api/ticket/{trio_id}")
assert rejected_tick["verification_status"] == "REJECTED"
assert rejected_tick["rejection_reason"] == "Duplicate college registration anomaly"
print(f"[PASS] 13. Admin reject workflow with mandatory reason verified ({rejected_tick['rejection_reason']})")

print("\n>>> ALL 13 E2E INTEGRATION TESTS PASSED PERFECTLY! <<<")
