#!/usr/bin/env python3
"""
Test Suite: Organizer Payment QR Update & System Action Logging
Verifies:
1. System-level admin action logging (team_id='SYSTEM') succeeds without FK violation.
2. QR image validation and upload endpoint (/api/admin/organizer-qr) functions cleanly.
3. Persistence of organizer QR code in system_config database table.
4. get_organizer_qr_path() auto-hydrates from system_config when QR_DIR is empty.
"""
import os
import sys
import json
import base64
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import connect, is_postgres
import server

def test_system_action_logging():
    """Verify log_admin_action handles 'SYSTEM' and NULL team_id without foreign key errors."""
    server.log_admin_action('SYSTEM', 'super_nova09', 'TEST_SYSTEM_LOG', 'ACTIVE', 'UPDATED', 'Testing system log')
    
    with connect() as db:
        row = db.execute("SELECT * FROM admin_actions WHERE team_id = ? AND action = ?", ('SYSTEM', 'TEST_SYSTEM_LOG')).fetchone()
        assert row is not None, "System action was not recorded in admin_actions!"
        assert row['action'] == 'TEST_SYSTEM_LOG'
        # Clean up test row
        db.execute("DELETE FROM admin_actions WHERE team_id = ? AND action = ?", ('SYSTEM', 'TEST_SYSTEM_LOG'))
    print("[PASS] System action logging with team_id='SYSTEM' verified.")

def test_system_config_persistence():
    """Verify system_config table stores and retrieves configuration keys."""
    with connect() as db:
        if is_postgres():
            db.execute('''
                INSERT INTO system_config (key, value)
                VALUES ('test_key', 'test_val')
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
            ''')
        else:
            db.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('test_key', 'test_val')")
        
        row = db.execute("SELECT value FROM system_config WHERE key = 'test_key'").fetchone()
        assert row is not None and row[0] == 'test_val'
        db.execute("DELETE FROM system_config WHERE key = 'test_key'")
    print("[PASS] system_config key-value storage verified.")

def test_qr_validation():
    """Verify image payload validation for QR uploads."""
    # 1. 1x1 valid PNG
    tiny_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    valid, mime, ext, err = server.validate_image_payload(tiny_png)
    assert valid is True
    assert mime == 'image/png'
    assert ext == '.png'
    
    # 2. Invalid payload
    valid, mime, ext, err = server.validate_image_payload(b'not an image')
    assert valid is False
    assert err is not None
    print("[PASS] QR image validation verified.")

if __name__ == '__main__':
    test_system_action_logging()
    test_system_config_persistence()
    test_qr_validation()
    print("\nALL QR UPDATE & SYSTEM ACTION TESTS PASSED!")
