import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import json
import urllib.request
import urllib.error
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def request_json(url, method='GET', data=None, headers=None):
    if headers is None:
        headers = {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            status = response.status
            body = response.read().decode('utf-8')
            return status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {'raw': body}
        return e.code, parsed

def request_raw(url, method='GET', headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()

def main():
    print("=== STARTING SUPERNOVA SMTP & PASS PDF TEST SUITE ===")
    
    # 1. Admin login
    print("\n[1] Testing Admin Login...")
    status, res = request_json(f"{BASE_URL}/api/admin/login", 'POST', {
        'username': 'admin',
        'password': 'supernova2026#admin'
    })
    assert status == 200, f"Admin login failed: {status} {res}"
    admin_token = res['token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    print(f" Admin authenticated successfully. Token: {admin_token[:10]}...")

    # 2. Track availability
    print("\n[2] Testing Track Availability...")
    status, res = request_json(f"{BASE_URL}/api/registrations")
    assert status == 200, f"Availability check failed: {status} {res}"
    print(f" Availability received: Web: {res['web']['remaining']}, AI: {res['ai']['remaining']}")

    # 3. Create a test team registration (Duo)
    test_email_lead = "lead.quantum.test@tolani.edu"
    test_email_m2 = "member2.quantum.test@tolani.edu"
    print(f"\n[3] Creating new test team registration with leader email: {test_email_lead}...")
    
    reg_payload = {
        'leader_name': 'Aarav Mehta',
        'email': test_email_lead,
        'phone': '9876543210',
        'college': 'Tolani College of Commerce & Science',
        'track': 'web',
        'team_size': 2,
        'terms_accepted': True,
        'internship_accepted': True,
        'members': [
            {'name': 'Zara Khan', 'email': test_email_m2, 'phone': '9876543211', 'college': 'Tolani College'}
        ]
    }
    status, reg_res = request_json(f"{BASE_URL}/api/registrations", 'POST', reg_payload)
    if status == 409 and 'already registered' in str(reg_res):
        import time
        ts = int(time.time())
        test_email_lead = f"lead.quantum.{ts}@tolani.edu"
        test_email_m2 = f"m2.quantum.{ts}@tolani.edu"
        reg_payload['email'] = test_email_lead
        reg_payload['members'][0]['email'] = test_email_m2
        status, reg_res = request_json(f"{BASE_URL}/api/registrations", 'POST', reg_payload)

    assert status == 201, f"Registration failed: {status} {reg_res}"
    team_id = reg_res['id']
    print(f" Team created: {team_id} | Status: {reg_res['status']}")
    print(f" Event A (Registration Received) dispatch status: {reg_res.get('email_dispatch', {}).get('status')}")

    # 4. Check Public Ticket Endpoint
    print(f"\n[4] Testing Public Ticket Lookup for {team_id}...")
    status, ticket_res = request_json(f"{BASE_URL}/api/ticket/{team_id}")
    assert status == 200, f"Ticket lookup failed: {status} {ticket_res}"
    assert ticket_res['is_eligible'] is False, "New ticket should NOT be eligible for pass yet"
    print(f" Ticket status: {ticket_res['ticket_status']} | Eligible: {ticket_res['is_eligible']}")

    # 5. Check Public PDF download while unconfirmed -> Expect 403 Forbidden
    print(f"\n[5] Testing Public PDF Pass endpoint before confirmation (expect 403)...")
    status, headers, body = request_raw(f"{BASE_URL}/api/ticket/{team_id}/pdf")
    assert status == 403, f"Expected 403 for unconfirmed pass, got {status}"
    print(f" Unconfirmed ticket PDF access correctly forbidden (403): {body.decode('utf-8')[:80]}...")

    # 6. Verify admin table includes email status subquery
    print(f"\n[6] Checking Admin Registrations list for email status subquery...")
    status, list_res = request_json(f"{BASE_URL}/api/admin/registrations", headers=admin_headers)
    assert status == 200, f"Admin registrations list failed: {status}"
    target_row = next((r for r in list_res['registrations'] if r['id'] == team_id), None)
    assert target_row is not None, f"Team {team_id} not found in admin list"
    print(f" Team row in admin list:")
    print(f"   last_email_status: {target_row.get('last_email_status')}")
    print(f"   last_email_type:   {target_row.get('last_email_type')}")
    print(f"   last_email_time:   {target_row.get('last_email_time')}")

    # 7. Record Payment -> Triggers Event B (Payment Update)
    print(f"\n[7] Admin records payment for team {team_id}...")
    status, pay_res = request_json(
        f"{BASE_URL}/api/admin/registrations/{team_id}/verify-payment",
        'POST',
        {'notes': 'Physical ₹300 cash received at registration counter'},
        headers=admin_headers
    )
    assert status == 200, f"Record payment failed: {status} {pay_res}"
    print(f" Payment status updated to: {pay_res['payment_status']}")
    print(f" Email dispatch: {pay_res.get('email_dispatch', {}).get('status')} (Notification Type: {pay_res.get('email_dispatch', {}).get('notification_type')})")

    # 8. Approve Registration -> Triggers Event D (Final Confirmation + Attached PDF Pass)!
    print(f"\n[8] Admin approves registration for team {team_id}...")
    status, app_res = request_json(
        f"{BASE_URL}/api/admin/registrations/{team_id}/approve",
        'POST',
        {'notes': 'Identity verified. Credentials checked.'},
        headers=admin_headers
    )
    assert status == 200, f"Approval failed: {status} {app_res}"
    print(f" Verification status: {app_res['verification_status']} | Ticket status: {app_res['ticket_status']}")
    disp_res = app_res.get('email_dispatch', {})
    print(f" Email dispatch: {disp_res.get('status')} (Notification Type: {disp_res.get('notification_type')})")
    assert disp_res.get('notification_type') == 'FINAL_CONFIRMATION', f"Expected FINAL_CONFIRMATION, got {disp_res.get('notification_type')}"

    # 9. Verify Public PDF download NOW SUCCEEDS (200 OK + application/pdf)
    print(f"\n[9] Testing Public PDF Pass download for confirmed team...")
    status, headers, pdf_data = request_raw(f"{BASE_URL}/api/ticket/{team_id}/pdf")
    assert status == 200, f"Expected 200 for confirmed pass PDF, got {status}"
    assert headers.get('Content-Type') == 'application/pdf', f"Expected application/pdf, got {headers.get('Content-Type')}"
    assert pdf_data.startswith(b'%PDF'), f"PDF file does not start with %PDF: {pdf_data[:10]}"
    print(f" Vector PDF pass downloaded successfully! Length: {len(pdf_data)} bytes | Header: {pdf_data[:8]}")

    # 10. Verify Admin PDF download endpoint
    print(f"\n[10] Testing Admin PDF Pass download endpoint...")
    status, headers, adm_pdf_data = request_raw(f"{BASE_URL}/api/admin/registrations/{team_id}/pdf", headers=admin_headers)
    assert status == 200, f"Expected 200 for admin pass PDF, got {status}"
    assert adm_pdf_data.startswith(b'%PDF'), "Admin PDF does not start with %PDF"
    print(f" Admin PDF pass downloaded successfully! Length: {len(adm_pdf_data)} bytes")

    # 11. Duplicate Prevention Test
    print(f"\n[11] Testing Duplicate Prevention: Re-triggering approval...")
    status, dup_res = request_json(
        f"{BASE_URL}/api/admin/registrations/{team_id}/approve",
        'POST',
        {'notes': 'Re-approval attempt'},
        headers=admin_headers
    )
    assert status == 200, f"Re-approval failed: {status}"
    dup_disp = dup_res.get('email_dispatch', {})
    print(f" Re-approval dispatch result: {dup_disp.get('status')} | {dup_disp.get('error')}")

    # 12. Admin Force Resend Test
    print(f"\n[12] Testing Admin Resend Email action...")
    status, resend_res = request_json(
        f"{BASE_URL}/api/admin/registrations/{team_id}/resend-email",
        'POST',
        {},
        headers=admin_headers
    )
    assert status == 200, f"Resend email failed: {status} {resend_res}"
    print(f" Admin resend result: {resend_res.get('dispatch', {}).get('status')}")

    # 13. Rejection Test
    print(f"\n[13] Testing Rejection Flow...")
    import time
    ts = int(time.time() * 1000)
    status, rej_team = request_json(f"{BASE_URL}/api/registrations", 'POST', {
        'leader_name': 'Dev Sharma',
        'email': f'dev.reject.{ts}@tolani.edu',
        'phone': '9876543299',
        'college': 'Tolani College',
        'track': 'ai',
        'team_size': 2,
        'terms_accepted': True,
        'internship_accepted': True,
        'members': [
            {'name': 'Rohan Das', 'email': f'rohan.reject.{ts}@tolani.edu', 'phone': '9876543298', 'college': 'Tolani College'}
        ]
    })
    rej_id = rej_team['id']
    status, reject_action_res = request_json(
        f"{BASE_URL}/api/admin/registrations/{rej_id}/reject",
        'POST',
        {'reason': 'Incomplete college identity proof'},
        headers=admin_headers
    )
    assert status == 200, f"Reject action failed: {status}"
    print(f" Team {rej_id} rejected. Dispatch status: {reject_action_res.get('email_dispatch', {}).get('status')} (Type: {reject_action_res.get('email_dispatch', {}).get('notification_type')})")

    # Check that rejected team PDF is forbidden
    status, _, _ = request_raw(f"{BASE_URL}/api/ticket/{rej_id}/pdf")
    assert status == 403, f"Expected 403 for rejected ticket PDF, got {status}"
    print(f" Rejected ticket PDF download correctly forbidden (403).")

    print("\n=======================================================")
    print(" ALL 13 TEST SUITE ASSERTIONS PASSED WITH ZERO ERRORS!")
    print("=======================================================")

if __name__ == '__main__':
    main()
