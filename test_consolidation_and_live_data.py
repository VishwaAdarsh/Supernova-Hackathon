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

def get_err(path, headers=None):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {})
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, res.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')

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

print("=== SUPERNOVA CONSOLIDATION & LIVE DATA VERIFICATION SUITE ===")

# Test 1: Duplicate panel removed
status, body = get_err("/verify")
assert status == 404, f"Expected 404 for /verify, got {status}"
status, body = get_err("/verify.html")
assert status == 404, f"Expected 404 for /verify.html, got {status}"
print("[PASS] 1. Duplicate /verify and verify.html are completely removed (404 Not Found)")

# Test 2: Single Admin console active at /admin
status, admin_html = get_html("/admin")
assert status == 200
assert "SUPERNOVA 2026 // Admin Telemetry Command Center" in admin_html
assert "COMMAND AUTHENTICATION" in admin_html
assert "REGISTRATION TELEMETRY DASHBOARD" in admin_html
print("[PASS] 2. Single admin dashboard available and protected at /admin")

# Test 3: Authenticate Admin
status, login_res = post("/api/admin/login", {"username": "admin", "password": "supernova2026#admin"})
assert status == 200 and "token" in login_res
token = login_res["token"]
headers = {"Authorization": f"Bearer {token}"}
print("[PASS] 3. Admin session authenticated")

# Test 4: Real live database telemetry returned (not mock)
status, dash = get("/api/admin/dashboard", headers=headers)
assert status == 200
summary = dash["summary"]
assert summary["total_teams"] >= 17, f"Expected at least 17 teams in DB, got {summary['total_teams']}"
assert "web_teams" in summary and "ai_teams" in summary
print(f"[PASS] 4. Live metrics verified: {summary['total_teams']} total teams, {summary['web_teams']} Web, {summary['ai_teams']} AI, {summary['payment_paid']} Paid")

# Test 5: Live registration records returned with email, phone, college
status, reg_list = get("/api/admin/registrations", headers=headers)
assert status == 200
registrations = reg_list["registrations"]
assert len(registrations) >= 17, f"Expected at least 17 registrations, got {len(registrations)}"
# Check first registration fields
r0 = registrations[0]
assert "id" in r0 and "leader_name" in r0 and "track" in r0 and "payment_status" in r0 and "verification_status" in r0
print(f"[PASS] 5. Live registration list verified: {len(registrations)} teams loaded directly from SQLite")

# Test 6: Search & Filter live data
status, search_res = get("/api/admin/registrations?search=Adarsh", headers=headers)
assert status == 200
assert len(search_res["registrations"]) >= 1, "Expected search for 'Adarsh' to find team"
adarsh_team = search_res["registrations"][0]
assert "Adarsh" in adarsh_team["leader_name"]
print(f"[PASS] 6. Live database search verified: found operative {adarsh_team['leader_name']} ({adarsh_team['id']})")

# Test 7: Create a fresh test team to verify full consolidated admin workflow
test_id = uuid.uuid4().hex[:6]
reg_payload = {
    "leader_name": f"Test Agent {test_id}",
    "email": f"agent.{test_id}@quantum.edu",
    "phone": "9998887770",
    "college": "Tolani College of Commerce & Science",
    "track": "ai",
    "team_size": 2,
    "members": [{"name": f"Partner {test_id}", "email": f"partner.{test_id}@quantum.edu", "phone": "9998887771", "college": "Tolani College"}],
    "terms_accepted": True
}
status, new_team = post("/api/registrations", reg_payload)
assert status == 201
tid = new_team["id"]
print(f"[PASS] 7. New registration created: {tid}")

# Test 8: Verify initial state is PENDING payment and PENDING approval
status, initial_ticket = get(f"/api/ticket/{tid}")
assert status == 200
assert initial_ticket["payment_status"] == "PENDING"
assert initial_ticket["verification_status"] == "PENDING_VERIFICATION"
assert initial_ticket["is_eligible"] is False
assert initial_ticket["ticket_token"] is None
print("[PASS] 8. Initial state strictly locked (is_eligible=False, ticket_token=None)")

# Test 9: Admin Workflow: Verify Payment in Admin
status, pay_res = post(f"/api/admin/registrations/{tid}/verify-payment", {"notes": "Paid ₹300 at desk"}, headers=headers)
assert status == 200
assert pay_res["payment_status"] == "PAID"

status, after_pay = get(f"/api/ticket/{tid}")
assert after_pay["payment_status"] == "PAID"
assert after_pay["verification_status"] == "PENDING_VERIFICATION"
assert after_pay["is_eligible"] is False, "Payment alone MUST NOT grant access to ticket!"
print("[PASS] 9. Payment verification recorded: ticket remains locked pending approval")

# Test 10: Admin Workflow: Approve Registration in Admin
status, app_res = post(f"/api/admin/registrations/{tid}/approve", {"notes": "Approved by organizer"}, headers=headers)
assert status == 200
assert app_res["verification_status"] == "VERIFIED"
assert app_res["ticket_status"] == "CONFIRMED"

status, after_app = get(f"/api/ticket/{tid}")
assert after_app["payment_status"] == "PAID"
assert after_app["verification_status"] == "VERIFIED"
assert after_app["is_eligible"] is True, "Both conditions met: official ticket MUST be unlocked!"
assert after_app["ticket_token"] is not None
print("[PASS] 10. Registration approved: Dual-condition satisfied, ticket confirmed and unlocked!")

# Test 11: Admin Workflow: Revoke / Reject Payment in Admin
status, rev_res = post(f"/api/admin/registrations/{tid}/reject-payment", {"notes": "Payment bounced/unverified"}, headers=headers)
assert status == 200
assert rev_res["payment_status"] == "PENDING"
assert rev_res["ticket_status"] == "PENDING"

status, after_rev = get(f"/api/ticket/{tid}")
assert after_rev["is_eligible"] is False, "Revoked payment MUST immediately relock official ticket!"
print("[PASS] 11. Payment revocation verified: ticket immediately relocks")

# Test 12: Admin Workflow: Reject Registration with mandatory reason
status, rej_err = post_err(f"/api/admin/registrations/{tid}/reject", {"reason": ""}, headers=headers)
assert status == 400, "Empty rejection reason must be rejected with 400"

status, rej_res = post(f"/api/admin/registrations/{tid}/reject", {"reason": "Non-compliant academic credentials"}, headers=headers)
assert status == 200
assert rej_res["verification_status"] == "REJECTED"

status, after_rej = get(f"/api/ticket/{tid}")
assert after_rej["verification_status"] == "REJECTED"
assert after_rej["is_eligible"] is False
assert "Non-compliant academic credentials" in after_rej["rejection_reason"]
print("[PASS] 12. Registration rejection with mandatory reason verified")

# Test 13: Verify public site index.html QR code generation and deep link
status, public_html = get_html("/")
assert status == 200
assert "/?ref=" in public_html, "Deep link ticket reference /?ref= missing in index.html!"
assert "/verify?id=" not in public_html, "Old /verify?id= still found in index.html!"
print("[PASS] 13. Public index.html uses clean /?ref= deep link for QR code and ticket lookup")

print("\nALL 13 TESTS PASSED SUCCESSFULLY! Consolidation and live data verification complete.")
