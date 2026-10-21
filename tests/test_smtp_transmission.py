import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import io
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.stdout.reconfigure(encoding='utf-8')

from email_service import send_email_notification, get_smtp_config

class TestSMTPTransmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure test SMTP env
        os.environ['SMTP_HOST'] = 'smtp.testserver.com'
        os.environ['SMTP_PORT'] = '587'
        os.environ['SMTP_USERNAME'] = 'supernova@testserver.com'
        os.environ['SMTP_PASSWORD'] = 'testsecretpassword'
        os.environ['SMTP_FROM_EMAIL'] = 'supernova@tolani.edu'
        os.environ['SMTP_FROM_NAME'] = 'SUPERNOVA 2026'
        os.environ['SMTP_USE_TLS'] = 'true'
        os.environ['SMTP_USE_SSL'] = 'false'

    def test_smtp_configuration_detection(self):
        cfg = get_smtp_config()
        self.assertTrue(cfg['is_configured'])
        self.assertEqual(cfg['host'], 'smtp.testserver.com')
        self.assertEqual(cfg['port'], 587)
        self.assertEqual(cfg['from_email'], 'supernova@tolani.edu')
        self.assertTrue(cfg['use_tls'])
        self.assertFalse(cfg['use_ssl'])

    def test_conflicting_tls_ssl_configuration(self):
        with patch.dict(os.environ, {'SMTP_USE_TLS': 'true', 'SMTP_USE_SSL': 'true'}):
            team = {
                'id': 'SN26-CFGTEST',
                'team_name': 'Config Test Team',
                'leader_name': 'Test Lead',
                'track': 'web',
                'team_size': 2,
                'email': 'lead@test.edu',
                'payment_status': 'PENDING',
                'verification_status': 'PENDING_VERIFICATION'
            }
            members = [{'name': 'Test Lead', 'email': 'lead@test.edu', 'role': 'leader'}]
            res = send_email_notification('REGISTRATION_RECEIVED', team, members)
            self.assertEqual(res['status'], 'CONFIG_ERROR')
            self.assertIn('cannot be enabled simultaneously', res['error'])

    @patch('smtplib.SMTP')
    def test_successful_final_confirmation_transmission(self, mock_smtp_cls):
        import uuid
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        unique_id = f"SN26-{uuid.uuid4().hex[:8].upper()}"
        team = {
            'id': unique_id,
            'team_name': 'Byte Force',
            'leader_name': 'Kavya Rao',
            'track': 'ai',
            'team_size': 2,
            'email': 'kavya.rao@tolani.edu',
            'payment_status': 'PAID',
            'verification_status': 'VERIFIED',
            'college': 'Tolani College of Commerce'
        }
        members = [
            {'name': 'Kavya Rao', 'email': 'kavya.rao@tolani.edu', 'role': 'leader', 'college': 'Tolani College'},
            {'name': 'Dev Joshi', 'email': 'dev.joshi@tolani.edu', 'role': 'member', 'college': 'Tolani College'}
        ]

        # 1. First send: Must succeed
        res = send_email_notification('FINAL_CONFIRMATION', team, members, force_resend=False)
        self.assertEqual(res['status'], 'SENT', f"Send failed: {res}")
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('supernova@testserver.com', 'testsecretpassword')
        mock_server.send_message.assert_called_once()

        sent_msg = mock_server.send_message.call_args[0][0]
        self.assertIn('Entry Pass for Team Byte Force', sent_msg['Subject'])
        self.assertEqual(sent_msg['To'], 'kavya.rao@tolani.edu')
        self.assertIn('SUPERNOVA 2026', sent_msg['From'])

        # Check PDF attachment
        attachments = [p for p in sent_msg.walk() if p.get_content_type() == 'application/pdf']
        self.assertEqual(len(attachments), 1)
        self.assertIn(f'SUPERNOVA_PASS_{unique_id}.pdf', attachments[0].get('Content-Disposition'))

        # 2. Second send without force_resend: Must be skipped as DUPLICATE_SKIPPED
        res_dup = send_email_notification('FINAL_CONFIRMATION', team, members, force_resend=False)
        self.assertEqual(res_dup['status'], 'DUPLICATE_SKIPPED')
        self.assertIn('already successfully sent', res_dup['error'])

        # 3. Third send with force_resend=True: Must succeed again
        res_forced = send_email_notification('FINAL_CONFIRMATION', team, members, force_resend=True)
        self.assertEqual(res_forced['status'], 'SENT')

    def test_dual_condition_gate_blocked(self):
        team_unpaid = {
            'id': 'SN26-GATEBLOCKED',
            'team_name': 'Pending Fee Team',
            'leader_name': 'Neil Patel',
            'track': 'web',
            'team_size': 2,
            'email': 'neil@tolani.edu',
            'payment_status': 'PENDING',
            'verification_status': 'VERIFIED'
        }
        res = send_email_notification('FINAL_CONFIRMATION', team_unpaid, [])
        self.assertEqual(res['status'], 'BLOCKED')
        self.assertIn('Pass requires BOTH payment_status == PAID and verification_status == VERIFIED', res['error'])

if __name__ == '__main__':
    unittest.main()
