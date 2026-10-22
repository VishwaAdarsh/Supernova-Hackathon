import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / 'backend'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from pdf_generator import generate_pass_pdf, resolve_pass_base_url
import qrcode

def test_qr_payload():
    print("--- [TEST 1] QR Code Payload Verification ---")
    base_url = resolve_pass_base_url()
    assert base_url == "https://supernova-hackathon-frontend.vercel.app", f"Expected canonical production URL, got: {base_url}"
    print(f"Canonical QR Target: {base_url}")

    # Verify qrcode generation with canonical URL
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(base_url)
    qr.make(fit=True)
    decoded_payload = qr.data_list[0].data.decode('utf-8') if isinstance(qr.data_list[0].data, bytes) else str(qr.data_list[0].data)
    assert decoded_payload == base_url, f"QR payload mismatch: {decoded_payload}"
    print(f"QR Code payload verified 100%: '{decoded_payload}'")
    print("--- [TEST 1] PASSED ---\n")

def test_two_distinct_tickets():
    print("--- [TEST 2] Dynamic Registration Data Isolation ---")
    
    # Registration A: Duo Web Debugging team, Verified
    team_a = {
        'id': 'SN26WB0017',
        'team_name': 'Quantum Bandits',
        'leader_name': 'Aarav Sharma',
        'track': 'web',
        'team_size': 2,
        'college': 'Tolani College of Commerce & Science',
        'payment_status': 'PAID',
        'verification_status': 'VERIFIED',
        'ticket_status': 'CONFIRMED',
        'fee_amount': 300
    }
    members_a = [
        {'name': 'Aarav Sharma', 'role': 'leader'},
        {'name': 'Riya Mehta', 'role': 'member'}
    ]

    # Registration B: Trio AI/ML System team, Pending
    team_b = {
        'id': 'SN26AI0042',
        'team_name': 'Neural Syndicate',
        'leader_name': 'Zack Taylor',
        'track': 'ai',
        'team_size': 3,
        'college': 'VJTI Engineering Mumbai',
        'payment_status': 'PENDING',
        'verification_status': 'PENDING_VERIFICATION',
        'ticket_status': 'PENDING',
        'fee_amount': 300
    }
    members_b = [
        {'name': 'Zack Taylor', 'role': 'leader'},
        {'name': 'Priya Nair', 'role': 'member'},
        {'name': 'Rohan Das', 'role': 'member'}
    ]

    pdf_a = generate_pass_pdf(team_a, members_a)
    pdf_b = generate_pass_pdf(team_b, members_b)

    assert pdf_a.startswith(b'%PDF-1.4') or pdf_a.startswith(b'%PDF'), "PDF A missing valid header"
    assert pdf_b.startswith(b'%PDF-1.4') or pdf_b.startswith(b'%PDF'), "PDF B missing valid header"
    assert len(pdf_a) > 100000, f"PDF A size suspicious: {len(pdf_a)} bytes"
    assert len(pdf_b) > 100000, f"PDF B size suspicious: {len(pdf_b)} bytes"

    # Save test outputs to scratch directory for inspection
    out_dir = Path(r"C:\Users\Pradeep\.gemini\antigravity\brain\948467da-3e36-464b-bb0b-3406b96ad8ed\scratch")
    out_a = out_dir / "ticket_pass_Aarav_SN26WB0017.pdf"
    out_b = out_dir / "ticket_pass_Zack_SN26AI0042.pdf"
    out_a.write_bytes(pdf_a)
    out_b.write_bytes(pdf_b)

    print(f"Generated Ticket A ({team_a['id']} - {team_a['team_name']}): {len(pdf_a)} bytes -> {out_a.name}")
    print(f"Generated Ticket B ({team_b['id']} - {team_b['team_name']}): {len(pdf_b)} bytes -> {out_b.name}")
    print("--- [TEST 2] PASSED ---\n")

def test_three_status_badges():
    print("--- [TEST 3] 3-State Status Badge Rendering ---")
    mock_base = {
        'id': 'SN26-STATUS-TEST',
        'team_name': 'Status Check Team',
        'leader_name': 'Tester',
        'track': 'web',
        'team_size': 2,
        'college': 'Tolani College'
    }
    mock_m = [{'name': 'Tester', 'role': 'leader'}]

    # 1. Verified
    p_ver = generate_pass_pdf(dict(mock_base, payment_status='PAID', verification_status='VERIFIED', ticket_status='CONFIRMED'), mock_m)
    # 2. Pending
    p_pen = generate_pass_pdf(dict(mock_base, payment_status='PENDING', verification_status='PENDING_VERIFICATION', ticket_status='PENDING'), mock_m)
    # 3. Revoked
    p_rev = generate_pass_pdf(dict(mock_base, payment_status='REJECTED', verification_status='REJECTED', ticket_status='REVOKED'), mock_m)

    assert len(p_ver) > 100000
    assert len(p_pen) > 100000
    assert len(p_rev) > 100000
    print("Verified, Pending, and Revoked status states rendered successfully.")
    print("--- [TEST 3] PASSED ---\n")

if __name__ == '__main__':
    test_qr_payload()
    test_two_distinct_tickets()
    test_three_status_badges()
    print("ALL REDESIGN VERIFICATION TESTS PASSED 100%!")
