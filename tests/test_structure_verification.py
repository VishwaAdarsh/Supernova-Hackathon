"""
SUPERNOVA 2026 - Restructured Architecture Verification Suite
Verifies frontend, backend, database separation, APIs, static assets, and security rules.
"""
import urllib.request
import urllib.error
import json
import unittest

BASE = "http://localhost:8000"

class TestStructureVerification(unittest.TestCase):

    def fetch(self, path, expected_status=200):
        url = f"{BASE}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, expected_status, f"Expected {expected_status} for {path}")
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, expected_status, f"Expected {expected_status} for {path}, got {e.code}")
            return e.code, e.read(), e.headers

    def test_frontend_routes(self):
        # Main landing page
        status, content, headers = self.fetch("/")
        self.assertEqual(status, 200)
        self.assertIn(b"SUPERNOVA", content)
        self.assertIn(b"text/html", headers.get("Content-Type", "").encode())

        # Admin dashboard
        status, content, headers = self.fetch("/admin")
        self.assertEqual(status, 200)
        self.assertIn(b"SUPERNOVA", content)

        # Legacy route supernova.html
        status, content, _ = self.fetch("/supernova.html")
        self.assertEqual(status, 200)
        self.assertIn(b"SUPERNOVA", content)

    def test_frontend_static_assets(self):
        for asset in [
            "/tolani-logo.jpg",
            "/horror-ambient.mp3",
            "/html2canvas.min.js",
            "/jspdf.umd.min.js",
            "/qrcode.min.js",
            "/assets/nova-avatar.png",
            "/assets/organizer-qr.jpg"
        ]:
            status, content, _ = self.fetch(asset)
            self.assertEqual(status, 200, f"Failed to fetch {asset}")
            self.assertGreater(len(content), 0, f"Empty content for {asset}")

    def test_database_ticket_api(self):
        # Fetch real registered team
        status, content, _ = self.fetch("/api/ticket/SN26-F5122A0DEB")
        self.assertEqual(status, 200)
        data = json.loads(content.decode("utf-8"))
        self.assertEqual(data["id"], "SN26-F5122A0DEB")
        self.assertEqual(data["team_name"], "Team karanmanikandan")
        self.assertEqual(data["track"], "web")
        self.assertEqual(data["verification_status"], "VERIFIED")
        self.assertEqual(data["is_eligible"], True)
        self.assertEqual(len(data["members"]), 2)

    def test_pdf_generation(self):
        status, content, headers = self.fetch("/api/ticket/SN26-F5122A0DEB/pdf")
        self.assertEqual(status, 200)
        self.assertTrue(content.startswith(b"%PDF"), "Must return a valid vector PDF")
        self.assertIn(b"application/pdf", headers.get("Content-Type", "").encode())
        self.assertGreater(len(content), 10000, "PDF size should be substantial")

    def test_security_protections(self):
        # Direct database file download must be blocked
        status, _, _ = self.fetch("/database/registrations.db", 403)
        self.assertEqual(status, 403)

        # Server source code download must be blocked
        status, _, _ = self.fetch("/backend/server.py", 403)
        self.assertEqual(status, 403)

        # Nonexistent files return 404
        status, _, _ = self.fetch("/nonexistent_sample.txt", 404)
        self.assertEqual(status, 404)

if __name__ == "__main__":
    unittest.main()
