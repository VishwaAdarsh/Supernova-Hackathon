import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

from pdf_generator import generate_pass_pdf, TRACK_DISPLAY_NAMES
from email_service import build_email_template, is_valid_email, get_smtp_config

def test_pdf_generation():
    print("--- [TEST] PDF Generation ---")
    mock_team = {
        'id': 'SN26-TEST-DUO-01',
        'team_name': 'Quantum Pioneers',
        'leader_name': 'Alice Smith',
        'track': 'web',
        'team_size': 2,
        'college': 'Tolani College of Commerce',
        'payment_status': 'PAID',
        'verification_status': 'VERIFIED',
        'ticket_status': 'CONFIRMED',
        'fee_amount': 300
    }
    mock_members = [
        {'name': 'Alice Smith', 'role': 'Lead', 'email': 'alice@example.com'},
        {'name': 'Bob Jones', 'role': 'Member', 'email': 'bob@example.com'}
    ]

    # 1. Verified pass
    pdf_bytes = generate_pass_pdf(mock_team, mock_members)
    assert pdf_bytes.startswith(b'%PDF'), "PDF output must begin with %PDF header"
    assert len(pdf_bytes) > 1000, f"PDF output suspiciously small: {len(pdf_bytes)} bytes"
    print(f"Verified Pass PDF generated: {len(pdf_bytes)} bytes")

    # 2. Pending pass
    mock_team_pending = dict(mock_team, payment_status='PENDING', verification_status='PENDING_VERIFICATION')
    pdf_pending = generate_pass_pdf(mock_team_pending, mock_members)
    assert pdf_pending.startswith(b'%PDF'), "Pending PDF output must begin with %PDF"
    print(f"Pending Pass PDF generated: {len(pdf_pending)} bytes")

    # 3. Revoked pass
    mock_team_revoked = dict(mock_team, payment_status='REJECTED', verification_status='REJECTED', ticket_status='REVOKED')
    pdf_revoked = generate_pass_pdf(mock_team_revoked, mock_members)
    assert pdf_revoked.startswith(b'%PDF'), "Revoked PDF output must begin with %PDF"
    print(f"Revoked Pass PDF generated: {len(pdf_revoked)} bytes")
    print("--- PDF Generation Tests PASSED ---\n")

def test_email_templates():
    print("--- [TEST] Email Templates ---")
    mock_team = {
        'id': 'SN26-TEST-DUO-01',
        'team_name': 'Quantum Pioneers',
        'leader_name': 'Alice Smith',
        'track': 'ai',
        'team_size': 2,
        'college': 'Tolani College of Commerce',
        'fee_amount': 300
    }
    mock_members = [
        {'name': 'Alice Smith', 'role': 'Lead', 'email': 'alice@example.com'},
        {'name': 'Bob Jones', 'role': 'Member', 'email': 'bob@example.com'}
    ]

    for event in ['REGISTRATION_RECEIVED', 'PAYMENT_UPDATE', 'FINAL_CONFIRMATION', 'APPROVAL_STATUS']:
        subj, text, html = build_email_template(event, mock_team, mock_members, extra={'notes': 'Test note'})
        assert len(subj) > 5, f"Subject too short for {event}"
        assert 'Alice Smith' in text or 'Quantum Pioneers' in text, f"Participant name missing in text for {event}"
        assert 'Alice Smith' in html or 'Quantum Pioneers' in html, f"Participant name missing in html for {event}"
        assert 'Tolani' in html, f"Tolani missing in footer for {event}"
        print(f"Template for {event}: Subject='{subj[:40]}...' OK")

    assert is_valid_email('test@example.com') is True
    assert is_valid_email('invalid-email') is False
    print("--- Email Template Tests PASSED ---\n")

def test_database_wrapper():
    print("--- [TEST] Database Wrapper ---")
    from database import connect, is_postgres
    with connect() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM teams").fetchone()
        cnt = row['cnt'] if 'cnt' in row.keys() else row[0]
        print(f"Connected successfully! Current teams in DB: {cnt} (is_postgres: {is_postgres()})")
        assert cnt >= 0
    print("--- Database Wrapper Tests PASSED ---\n")

if __name__ == '__main__':
    test_pdf_generation()
    test_email_templates()
    test_database_wrapper()
    print("ALL CORE UNIT TESTS PASSED SUCCESSFULLY!")
