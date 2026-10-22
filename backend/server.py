import base64
import binascii
import csv
import hmac
import io
import json
import os
import re
import secrets
import smtplib
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ROOT = BACKEND_DIR.parent

from database import (
    connect, is_postgres, DatabaseError, IntegrityError,
    upload_proof_to_supabase, fetch_proof_from_supabase,
    get_database_url, init_and_migrate_db, get_database_diagnostics, SQLITE_PATH
)
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit, unquote

from email_service import send_email_notification, get_smtp_config, load_dotenv
from pdf_generator import generate_pass_pdf

# Load local environment configuration if present
load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
FRONTEND_DIR = ROOT / 'frontend'
DATABASE_DIR = ROOT / 'database'
DATABASE = (DATABASE_DIR / 'registrations.db') if (DATABASE_DIR / 'registrations.db').exists() else (ROOT / 'registrations.db')
DISPATCH_LOG = ROOT / 'email_dispatch_log.txt'

# Storage directories for payments and organizer QR
UPLOADS_DIR = ROOT / 'uploads'
QR_DIR = UPLOADS_DIR / 'qr'
PROOFS_DIR = UPLOADS_DIR / 'proofs'
QR_DIR.mkdir(parents=True, exist_ok=True)
PROOFS_DIR.mkdir(parents=True, exist_ok=True)

# Track capacities as per event specification
CAPACITIES = {'web': 15, 'ai': 25}

# Track normalization mappings
TRACK_MAP = {
    'web': 'web',
    'web_debugging': 'web',
    'web debugging': 'web',
    'ai': 'ai',
    'aiml': 'ai',
    'ai_ml': 'ai',
    'ai / ml': 'ai',
    'ai/ml': 'ai'
}

TRACK_NAMES = {
    'web': 'Web Debugging',
    'ai': 'AI / ML System'
}

# Admin Credentials (configurable via environment variables)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'supernova2026#admin')

# Confirmed Event Registration Fee
CONFIRMED_FEE_AMOUNT = int(os.environ.get('EVENT_FEE_AMOUNT', 300))
CONFIRMED_FEE_LABEL = os.environ.get('EVENT_FEE_LABEL', '₹300 Flat per Team')

# Organizer Official UPI Details
ORGANIZER_UPI_ID = os.environ.get('ORGANIZER_UPI_ID', 'swainpapa@fam')
ORGANIZER_UPI_NAME = os.environ.get('ORGANIZER_UPI_NAME', 'ARRAMAN SWAIN')

def get_organizer_qr_path():
    """Returns the Path to the configured organizer payment QR image or None."""
    qr_files = [f for f in QR_DIR.glob('organizer_qr.*') if f.is_file() and f.stat().st_size > 0]
    if qr_files:
        qr_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return qr_files[0]
    # Fallback to assets
    for p_asset in [ROOT / 'assets' / 'organizer-qr.jpg', ROOT / 'assets' / 'organizer-qr.png', ROOT / 'assets' / 'organizer-qr.webp']:
        if p_asset.is_file() and p_asset.stat().st_size > 0:
            return p_asset
    return None

def validate_image_payload(raw_bytes, max_bytes=5 * 1024 * 1024):
    """Validates image size and magic bytes. Returns (is_valid, mime_type, extension, error_message)."""
    if not raw_bytes or len(raw_bytes) == 0:
        return False, None, None, "Uploaded file is empty."
    if len(raw_bytes) > max_bytes:
        return False, None, None, f"File size ({len(raw_bytes) / 1024 / 1024:.2f} MB) exceeds maximum limit of {max_bytes / 1024 / 1024:.0f} MB."
    
    # Check Magic Bytes
    if raw_bytes[:3] == b'\xff\xd8\xff':
        return True, 'image/jpeg', '.jpg', None
    elif raw_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return True, 'image/png', '.png', None
    elif raw_bytes[:4] == b'RIFF' and len(raw_bytes) > 12 and raw_bytes[8:12] == b'WEBP':
        return True, 'image/webp', '.webp', None
    else:
        return False, None, None, "Invalid image format. Only JPEG, PNG, and WebP images are allowed."

# connect() is imported from database.py (supports PostgreSQL & SQLite fallback)

def build_ticket_payload(team, members, already_registered=False):
    """Builds a rich, consistent status & pass response dictionary for a team."""
    is_eligible = (team['payment_status'] == 'PAID' and team['verification_status'] == 'VERIFIED')
    effective_ticket_status = 'CONFIRMED' if is_eligible else ('REJECTED' if team['verification_status'] == 'REJECTED' else 'PENDING')

    if is_eligible:
        status_message = "You're officially registered for SUPERNOVA!"
    elif team['verification_status'] == 'REJECTED':
        status_message = f"Registration rejected: {team['rejection_reason'] or 'Criteria not satisfied'}"
    elif team['payment_status'] == 'REJECTED':
        status_message = f"Payment proof rejected: {team['payment_review_notes'] or team['rejection_reason'] or 'Transaction details could not be verified'}. Please upload a replacement screenshot."
    elif team['payment_status'] == 'PENDING_REVIEW':
        status_message = "Payment proof submitted successfully. Your payment is pending admin verification."
    elif team['payment_status'] == 'PAID':
        status_message = "Payment verified. Awaiting organizer clearance."
    else:
        status_message = "Registration received. Please complete UPI payment and upload your screenshot."

    has_proof = bool(team['proof_path'] or team['proof'])
    lead_member = members[0] if members else None
    college = (lead_member['college'] if lead_member and 'college' in lead_member.keys() and lead_member['college'] else 'Tolani College of Commerce & Science')
    leader_email = (lead_member['email'] if lead_member and 'email' in lead_member.keys() and lead_member['email'] else '')

    payload = {
        'id': team['id'],
        'team_name': team['team_name'],
        'leader_name': team['leader_name'],
        'email': leader_email,
        'track': team['track'],
        'track_label': TRACK_NAMES.get(team['track'], team['track'].upper()),
        'track_key': team['track'],
        'team_size': team['team_size'],
        'college': college,
        'members': [m['name'] for m in members],
        'payment_status': team['payment_status'],
        'verification_status': team['verification_status'],
        'ticket_status': effective_ticket_status,
        'is_eligible': is_eligible,
        'status_message': status_message,
        'has_proof': has_proof,
        'proof_url': f"/api/ticket/{team['id']}/proof" if has_proof else None,
        'transaction_id': team['transaction_id'],
        'payment_submitted_at': team['payment_submitted_at'],
        'payment_reviewed_at': team['payment_reviewed_at'],
        'payment_review_notes': team['payment_review_notes'],
        'ticket_token': team['ticket_token'] if is_eligible else None,
        'fee_amount': team['fee_amount'],
        'fee_formatted': CONFIRMED_FEE_LABEL,
        'fee': CONFIRMED_FEE_LABEL,
        'status': team['status'],
        'rejection_reason': team['rejection_reason'] if team['verification_status'] == 'REJECTED' else None,
        'created_at': team['created_at']
    }
    if already_registered:
        payload['already_registered'] = True
        payload['message'] = f"Welcome back, Team {team['team_name'] or team['leader_name']}! Live registration status & pass retrieved."
    return payload

def resolve_public_base_url(headers=None):
    """
    Authoritative public URL resolver for passes, QR codes, verification links, and email notifications.
    Prioritizes explicit environment configurations (FRONTEND_URL, PUBLIC_BASE_URL),
    falling back to Host/X-Forwarded headers or the canonical production Vercel frontend.
    """
    env_url = (
        os.environ.get('FRONTEND_URL')
        or os.environ.get('PUBLIC_FRONTEND_URL')
        or os.environ.get('NEXT_PUBLIC_APP_URL')
        or os.environ.get('PUBLIC_BASE_URL')
        or os.environ.get('PASS_BASE_URL')
    )
    if env_url:
        return env_url.strip().rstrip('/')

    if headers:
        proto = headers.get('X-Forwarded-Proto', 'https' if (headers.get('Host', '').endswith('.render.com') or headers.get('Host', '').endswith('.vercel.app')) else 'http')
        host = headers.get('X-Forwarded-Host') or headers.get('Host')
        if host:
            if 'onrender.com' in host.lower():
                return 'https://supernova-hackathon-frontend.vercel.app'
            return f"{proto}://{host}".rstrip('/')

    return 'https://supernova-hackathon-frontend.vercel.app'

# Initial schema initialization happens dynamically via backend.database
try:
    init_and_migrate_db()
except Exception as _e:
    print(f"[DATABASE WARNING] Initial schema migration check: {_e}")

# --- Admin Authentication Helpers ---
def create_admin_session(username):
    token = secrets.token_hex(32)
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(hours=24)
    with connect() as db:
        if getattr(db, 'is_postgres', False):
            db.execute(
                'INSERT INTO admin_sessions (token, username, expires_at) VALUES (?, ?, ?)',
                (token, username, expires_at)
            )
        else:
            db.execute(
                'INSERT INTO admin_sessions (token, username, expires_at) VALUES (?, ?, ?)',
                (token, username, expires_at.isoformat())
            )
    return token, expires_at.isoformat()

def verify_admin_session(token):
    if not token:
        return None
    if token == 'BASIC_AUTH_ADMIN':
        return ADMIN_USERNAME
    try:
        with connect() as db:
            row = db.execute(
                'SELECT username, expires_at FROM admin_sessions WHERE token = ?',
                (token,)
            ).fetchone()
            if not row:
                return None
            
            exp_val = row['expires_at']
            if isinstance(exp_val, str):
                exp = datetime.fromisoformat(exp_val)
            elif isinstance(exp_val, datetime):
                exp = exp_val
            else:
                return None

            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)

            if exp < datetime.now(timezone.utc):
                db.execute('DELETE FROM admin_sessions WHERE token = ?', (token,))
                return None
            return row['username']
    except Exception as e:
        print(f"[AUTH ERROR] Session verification failed: {e}")
        return None

def revoke_admin_session(token):
    if token:
        with connect() as db:
            db.execute('DELETE FROM admin_sessions WHERE token = ?', (token,))

def log_admin_action(team_id, admin_user, action, previous_status, new_status, notes=''):
    with connect() as db:
        db.execute('''
            INSERT INTO admin_actions (team_id, admin_user, action, previous_status, new_status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (team_id, admin_user, action, previous_status, new_status, notes))

# --- Email Notification Service Delegation ---
def send_confirmation_email(team, members, force_resend=False, base_url=None):
    if not base_url or base_url == "http://localhost:8000":
        base_url = resolve_public_base_url()
    """
    Sends the official registration confirmation email with PDF pass attached.
    Delegates to email_service.send_email_notification with strict dual-condition validation
    and duplicate prevention.
    """
    return send_email_notification('FINAL_CONFIRMATION', team, members, force_resend=force_resend, base_url=base_url)


class Server(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        raw = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Cache-Control, Pragma, X-Requested-With, Accept')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        """Handle CORS preflight cleanly."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, Cache-Control, Pragma, X-Requested-With, Accept')
        self.send_header('Access-Control-Max-Age', '86400')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def get_auth_token(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth[7:].strip()
        if auth.startswith('Basic '):
            try:
                decoded = base64.b64decode(auth[6:].strip()).decode('utf-8')
                if ':' in decoded:
                    u, p = decoded.split(':', 1)
                    if hmac.compare_digest(u.encode(), ADMIN_USERNAME.encode()) and hmac.compare_digest(p.encode(), ADMIN_PASSWORD.encode()):
                        return 'BASIC_AUTH_ADMIN'
            except Exception:
                pass
        parsed = urlsplit(self.path)
        q = parse_qs(parsed.query)
        token_q = q.get('token', [None])[0]
        if token_q:
            return token_q.strip()
        return None

    def read_json_body(self):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 6 * 1024 * 1024:
            raise ValueError('Invalid payload size.')
        raw_body = self.rfile.read(length)
        data = json.loads(raw_body.decode('utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Request body must be a JSON object.')
        return data

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # ---------------------------------------------------------
        # Health & Persistence Diagnostics Endpoint
        # ---------------------------------------------------------
        if path in ('/health', '/api/health'):
            diag = get_database_diagnostics()
            status_code = 503 if diag.get('connection_error') else 200
            return self.send_json(status_code, {
                'status': 'healthy' if status_code == 200 else 'degraded',
                'service': 'supernova-registration-server',
                'persistence_tier': diag.get('persistence_tier'),
                'engine': diag.get('engine'),
                'is_persistent': diag.get('is_persistent'),
                'teams_count': diag.get('teams_count'),
                'members_count': diag.get('members_count'),
                'error': diag.get('connection_error')
            })

        # ---------------------------------------------------------
        # API: Real-time track availability
        # ---------------------------------------------------------
        if path == '/api/registrations':
            try:
                with connect() as db:
                    rows = db.execute('SELECT track, COUNT(*) as count FROM teams GROUP BY track').fetchall()
                    used = {row['track']: row['count'] for row in rows}

                web_total = CAPACITIES['web']
                web_used = used.get('web', 0)
                web_remaining = max(0, web_total - web_used)

                ai_total = CAPACITIES['ai']
                ai_used = used.get('ai', 0)
                ai_remaining = max(0, ai_total - ai_used)

                data = {
                    'web': {
                        'total': web_total,
                        'claimed': min(web_total, web_used),
                        'remaining': web_remaining
                    },
                    'ai': {
                        'total': ai_total,
                        'claimed': min(ai_total, ai_used),
                        'remaining': ai_remaining
                    },
                    'aiml': {
                        'total': ai_total,
                        'claimed': min(ai_total, ai_used),
                        'remaining': ai_remaining
                    }
                }
                return self.send_json(200, data)
            except (sqlite3.Error, DatabaseError):
                return self.send_json(503, {'error': 'Live availability temporarily unavailable.'})

        # ---------------------------------------------------------
        # API: Official Organizer Payment QR Configuration
        # ---------------------------------------------------------
        if path == '/api/organizer-qr':
            qr_p = get_organizer_qr_path()
            mtime = int(qr_p.stat().st_mtime) if qr_p and qr_p.is_file() else 0
            qr_url = f'/api/organizer-qr/image?v={mtime}' if qr_p else None
            return self.send_json(200, {
                'configured': qr_p is not None,
                'has_qr': qr_p is not None,
                'qr_url': qr_url,
                'image_url': qr_url,
                'version': mtime,
                'amount': CONFIRMED_FEE_AMOUNT,
                'fee_amount': CONFIRMED_FEE_AMOUNT,
                'fee_formatted': CONFIRMED_FEE_LABEL,
                'beneficiary': ORGANIZER_UPI_NAME,
                'beneficiary_name': ORGANIZER_UPI_NAME,
                'upi_id': ORGANIZER_UPI_ID
            })

        if path == '/api/organizer-qr/image':
            qr_p = get_organizer_qr_path()
            if not qr_p or not qr_p.is_file():
                return self.send_json(404, {'error': 'No organizer payment QR code configured by organizers.'})
            raw = qr_p.read_bytes()
            ext = qr_p.suffix.lower()
            mime = 'image/png' if ext == '.png' else ('image/webp' if ext == '.webp' else 'image/jpeg')
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(raw)
            return

        # ---------------------------------------------------------
        # API: Public Ticket Retrieval & PDF Pass
        # ---------------------------------------------------------
        if path.startswith('/api/ticket/'):
            # Check for PDF pass request: /api/ticket/<ref>/pdf or /api/ticket/<ref>/pass.pdf
            m_ticket_pdf = re.match(r'^/api/ticket/([^/]+)/(?:pdf|pass\.pdf)$', path)
            if m_ticket_pdf:
                ref = unquote(m_ticket_pdf.group(1).strip())
                with connect() as db:
                    team = db.execute('''
                        SELECT id, team_name, leader_name, track, team_size, 
                               payment_status, verification_status, ticket_status, ticket_token,
                               rejection_reason, fee_amount, member_names, created_at, status
                        FROM teams 
                        WHERE id = ? 
                           OR ticket_token = ?
                           OR id IN (
                               SELECT m.team_id 
                               FROM members m 
                               JOIN teams t ON t.id = m.team_id 
                               WHERE LOWER(m.email) = LOWER(?)
                               ORDER BY (CASE WHEN t.payment_status = 'PAID' AND t.verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, t.created_at DESC
                               LIMIT 1
                           )
                        ORDER BY (CASE WHEN payment_status = 'PAID' AND verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, created_at DESC
                        LIMIT 1
                    ''', (ref, ref, ref)).fetchone()

                    if not team:
                        return self.send_json(404, {'error': 'Ticket reference not found.'})

                    is_eligible = (team['payment_status'] == 'PAID' and team['verification_status'] == 'VERIFIED')
                    if not is_eligible:
                        return self.send_json(403, {
                            'error': 'Official PDF pass is locked. Requires both payment verification (₹300 flat fee) and organizer approval.'
                        })

                    members = [dict(m) for m in db.execute('''
                        SELECT name, role, email, phone, college FROM members WHERE team_id = ? ORDER BY id ASC
                    ''', (team['id'],)).fetchall()]

                team_dict = dict(team)
                base_url = resolve_public_base_url(self.headers)
                pdf_bytes = generate_pass_pdf(team_dict, members, base_url=base_url)

                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename="SUPERNOVA_PASS_{team["id"]}.pdf"')
                self.send_header('Content-Length', str(len(pdf_bytes)))
                self.send_header('Cache-Control', 'private, no-cache')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return

            # Check for participant viewing their own proof: /api/ticket/<ref>/proof
            m_ticket_proof = re.match(r'^/api/ticket/([^/]+)/proof$', path)
            if m_ticket_proof:
                ref = unquote(m_ticket_proof.group(1).strip())
                with connect() as db:
                    row = db.execute('''
                        SELECT id, proof, proof_type, proof_path FROM teams 
                        WHERE id = ? 
                           OR ticket_token = ?
                           OR id IN (
                               SELECT m.team_id 
                               FROM members m 
                               JOIN teams t ON t.id = m.team_id 
                               WHERE LOWER(m.email) = LOWER(?)
                               ORDER BY (CASE WHEN t.payment_status = 'PAID' AND t.verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, t.created_at DESC
                               LIMIT 1
                           )
                        ORDER BY (CASE WHEN payment_status = 'PAID' AND verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, created_at DESC
                        LIMIT 1
                    ''', (ref, ref, ref)).fetchone()
                    if not row or (not row['proof'] and not row['proof_path']):
                        return self.send_json(404, {'error': 'No payment screenshot uploaded for this registration.'})

                    proof_data = None
                    ptype = row['proof_type'] or 'image/jpeg'
                    if row['proof_path'] and row['proof_path'].startswith('supabase://'):
                        res = fetch_proof_from_supabase(row['proof_path'])
                        if res:
                            proof_data, ptype = res
                    elif row['proof_path']:
                        p_file = ROOT / row['proof_path']
                        if p_file.is_file():
                            proof_data = p_file.read_bytes()
                    if not proof_data and row['proof']:
                        proof_data = row['proof']
                        if isinstance(proof_data, memoryview):
                            proof_data = bytes(proof_data)

                    if not proof_data:
                        return self.send_json(404, {'error': 'Proof file missing on server.'})

                    self.send_response(200)
                    self.send_header('Content-Type', ptype)
                    self.send_header('Content-Length', str(len(proof_data)))
                    self.send_header('Cache-Control', 'private, max-age=60')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(proof_data)
                    return

            ref = path[len('/api/ticket/'):].strip()
            if '?' in ref:
                ref = ref.split('?')[0].strip()
            clean_ref = unquote(ref).strip()
            if not clean_ref or len(clean_ref) > 128:
                return self.send_json(400, {'error': 'Invalid ticket reference or email.'})

            with connect() as db:
                team = db.execute('''
                    SELECT id, team_name, leader_name, track, team_size, 
                           payment_status, verification_status, ticket_status, ticket_token,
                           rejection_reason, fee_amount, member_names, created_at, status,
                           proof, proof_path, proof_type, transaction_id,
                           payment_submitted_at, payment_reviewed_at, payment_review_notes
                    FROM teams 
                    WHERE id = ? 
                       OR ticket_token = ?
                       OR id IN (
                           SELECT m.team_id 
                           FROM members m 
                           JOIN teams t ON t.id = m.team_id 
                           WHERE LOWER(m.email) = LOWER(?)
                           ORDER BY (CASE WHEN t.payment_status = 'PAID' AND t.verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, t.created_at DESC
                           LIMIT 1
                       )
                    ORDER BY (CASE WHEN payment_status = 'PAID' AND verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, created_at DESC
                    LIMIT 1
                ''', (clean_ref, clean_ref, clean_ref)).fetchone()

                if not team:
                    return self.send_json(404, {'error': 'Registration not found for reference or registered email.'})

                members = db.execute('''
                    SELECT name, role, email, phone, college FROM members WHERE team_id = ? ORDER BY id ASC
                ''', (team['id'],)).fetchall()

            payload = build_ticket_payload(team, members)
            return self.send_json(200, payload)

        # ---------------------------------------------------------
        # API: Admin Protected Routes
        # ---------------------------------------------------------
        if path.startswith('/api/admin/'):
            token = self.get_auth_token()
            admin_user = verify_admin_session(token)
            if not admin_user:
                return self.send_json(401, {'error': 'Unauthorized: Valid admin session token required.'})

            # GET /api/admin/diagnostics
            if path == '/api/admin/diagnostics':
                diag = get_database_diagnostics()
                return self.send_json(200, diag)

            # GET /api/admin/dashboard
            if path == '/api/admin/dashboard':
                with connect() as db:
                    total = db.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
                    web_count = db.execute("SELECT COUNT(*) FROM teams WHERE track = 'web'").fetchone()[0]
                    ai_count = db.execute("SELECT COUNT(*) FROM teams WHERE track = 'ai'").fetchone()[0]
                    pending_ver = db.execute("SELECT COUNT(*) FROM teams WHERE verification_status = 'PENDING_VERIFICATION'").fetchone()[0]
                    verified = db.execute("SELECT COUNT(*) FROM teams WHERE verification_status = 'VERIFIED'").fetchone()[0]
                    rejected = db.execute("SELECT COUNT(*) FROM teams WHERE verification_status = 'REJECTED'").fetchone()[0]
                    pending_pay = db.execute("SELECT COUNT(*) FROM teams WHERE payment_status = 'PENDING'").fetchone()[0]
                    pending_pay_review = db.execute("SELECT COUNT(*) FROM teams WHERE payment_status = 'PENDING_REVIEW'").fetchone()[0]
                    rejected_pay = db.execute("SELECT COUNT(*) FROM teams WHERE payment_status = 'REJECTED'").fetchone()[0]
                    paid = db.execute("SELECT COUNT(*) FROM teams WHERE payment_status = 'PAID'").fetchone()[0]
                    recent_actions = db.execute('''
                        SELECT * FROM admin_actions ORDER BY id DESC LIMIT 8
                    ''').fetchall()

                return self.send_json(200, {
                    'admin_user': admin_user,
                    'capacities': CAPACITIES,
                    'summary': {
                        'total_teams': total,
                        'web_teams': web_count,
                        'ai_teams': ai_count,
                        'pending_verification': pending_ver,
                        'verified': verified,
                        'rejected': rejected,
                        'payment_pending': pending_pay,
                        'payment_pending_review': pending_pay_review,
                        'payment_rejected': rejected_pay,
                        'payment_paid': paid
                    },
                    'recent_actions': [dict(r) for r in recent_actions]
                })

            # GET /api/admin/export/csv
            if path == '/api/admin/export/csv':
                filter_status = query.get('status', ['ALL'])[0].strip().upper()
                filter_track = query.get('track', ['ALL'])[0].strip().lower()

                sql = 'SELECT * FROM teams WHERE 1=1'
                params = []

                if filter_track in ('web', 'ai'):
                    sql += ' AND track = ?'
                    params.append(filter_track)

                if filter_status == 'VERIFIED':
                    sql += " AND verification_status = 'VERIFIED' AND payment_status = 'PAID'"
                elif filter_status == 'PENDING_REVIEW':
                    sql += " AND payment_status = 'PENDING_REVIEW'"
                elif filter_status == 'PENDING':
                    sql += " AND (verification_status != 'VERIFIED' OR payment_status != 'PAID') AND verification_status != 'REJECTED' AND payment_status != 'REJECTED'"
                elif filter_status == 'PAID':
                    sql += " AND payment_status = 'PAID'"
                elif filter_status == 'REJECTED':
                    sql += " AND (verification_status = 'REJECTED' OR payment_status = 'REJECTED')"
                elif filter_status == 'PAY_REJECTED':
                    sql += " AND payment_status = 'REJECTED'"

                sql += ' ORDER BY created_at ASC'

                with connect() as db:
                    team_rows = [dict(r) for r in db.execute(sql, params).fetchall()]
                    all_members = [dict(m) for m in db.execute('SELECT * FROM members ORDER BY team_id, id ASC').fetchall()]
                    members_by_team = {}
                    for m in all_members:
                        members_by_team.setdefault(m['team_id'], []).append(m)

                output = io.StringIO()
                writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

                writer.writerow([
                    'Registration ID',
                    'Registration Date',
                    'Team Name',
                    'Team Size',
                    'Selected Track',
                    'Leader Name',
                    'Leader Email',
                    'Leader Phone',
                    'Leader College',
                    'Member 2 Name',
                    'Member 2 Email',
                    'Member 2 Phone',
                    'Member 2 College',
                    'Member 3 Name',
                    'Member 3 Email',
                    'Member 3 Phone',
                    'Member 3 College',
                    'Fee Amount (INR)',
                    'Payment Status',
                    'Payment Ref / UTR',
                    'Verification Status',
                    'Pass Status'
                ])

                for t in team_rows:
                    t_members = members_by_team.get(t['id'], [])
                    leader = None
                    for m in t_members:
                        if m.get('role') == 'leader':
                            leader = m
                            break
                    if not leader and t_members:
                        leader = t_members[0]
                    if not leader:
                        leader = {}

                    other_members = [m for m in t_members if m is not leader]
                    m2 = other_members[0] if len(other_members) > 0 else {}
                    m3 = other_members[1] if len(other_members) > 1 else {}

                    t_size = t.get('team_size', 2)
                    team_size_label = f"{t_size} (Duo)" if t_size == 2 else f"{t_size} (Trio)"
                    track_name = TRACK_NAMES.get(t.get('track'), t.get('track', ''))
                    team_name = t.get('team_name') or f"Team {t.get('leader_name') or leader.get('name', '')}"

                    writer.writerow([
                        t.get('id', ''),
                        t.get('created_at', ''),
                        team_name,
                        team_size_label,
                        track_name,
                        leader.get('name') or t.get('leader_name', ''),
                        leader.get('email', ''),
                        leader.get('phone', ''),
                        leader.get('college', ''),
                        m2.get('name', ''),
                        m2.get('email', ''),
                        m2.get('phone', ''),
                        m2.get('college', ''),
                        m3.get('name', ''),
                        m3.get('email', ''),
                        m3.get('phone', ''),
                        m3.get('college', ''),
                        t.get('fee_amount', 300),
                        t.get('payment_status', 'PENDING'),
                        t.get('transaction_id', '') or '',
                        t.get('verification_status', 'PENDING_VERIFICATION'),
                        t.get('ticket_status', 'PENDING')
                    ])

                csv_content = output.getvalue()
                csv_bytes = csv_content.encode('utf-8-sig')

                now_str = datetime.now().strftime('%Y-%m-%d')
                filename = f"supernova_2026_team_registrations_{now_str}.csv"

                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                self.send_header('Content-Length', str(len(csv_bytes)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
                self.end_headers()
                self.wfile.write(csv_bytes)
                return

            # GET /api/admin/registrations
            if path == '/api/admin/registrations':
                search_term = query.get('search', [''])[0].strip()
                filter_track = query.get('track', [''])[0].strip().lower()
                filter_ver = query.get('verification_status', [''])[0].strip().upper()
                filter_pay = query.get('payment_status', [''])[0].strip().upper()

                sql = '''
                    SELECT t.*, 
                           (SELECT COUNT(*) FROM members m WHERE m.team_id = t.id) as roster_count,
                           (SELECT email FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) as email,
                           (SELECT phone FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) as phone,
                           (SELECT college FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) as college,
                           (SELECT status FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_status,
                           (SELECT sent_at FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_time,
                           (SELECT notification_type FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_type,
                           (SELECT error_message FROM email_dispatches e WHERE e.team_id = t.id ORDER BY e.id DESC LIMIT 1) as last_email_error
                    FROM teams t WHERE 1=1
                '''
                params = []

                if search_term:
                    sql += ''' AND (t.id LIKE ? OR t.team_name LIKE ? OR t.leader_name LIKE ?
                                    OR (SELECT email FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) LIKE ?
                                    OR (SELECT college FROM members m WHERE m.team_id = t.id ORDER BY id ASC LIMIT 1) LIKE ?)'''
                    q = f"%{search_term}%"
                    params.extend([q, q, q, q, q])
                if filter_track in CAPACITIES:
                    sql += ' AND t.track = ?'
                    params.append(filter_track)
                if filter_ver:
                    sql += ' AND t.verification_status = ?'
                    params.append(filter_ver)
                if filter_pay:
                    sql += ' AND t.payment_status = ?'
                    params.append(filter_pay)

                sql += ' ORDER BY t.created_at DESC'

                with connect() as db:
                    rows = db.execute(sql, params).fetchall()
                    data = []
                    for r in rows:
                        d = dict(r)
                        d.pop('proof', None)  # do not send raw blob in list view
                        d['has_proof'] = bool(r['proof_path'] or r['proof'])
                        d['proof_url'] = f"/api/admin/registrations/{d['id']}/proof" if d['has_proof'] else None
                        d['track_label'] = TRACK_NAMES.get(d['track'], d['track'])
                        data.append(d)

                return self.send_json(200, {'registrations': data, 'teams': data, 'count': len(data)})

            # GET /api/admin/registrations/<id>
            m_single = re.match(r'^/api/admin/registrations/([a-zA-Z0-9_\-]+)$', path)
            if m_single:
                team_id = m_single.group(1)
                with connect() as db:
                    team_row = db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone()
                    if not team_row:
                        return self.send_json(404, {'error': 'Registration record not found.'})

                    team_dict = dict(team_row)
                    team_dict.pop('proof', None)
                    team_dict['has_proof'] = bool(team_row['proof_path'] or team_row['proof'])
                    team_dict['proof_url'] = f"/api/admin/registrations/{team_id}/proof" if team_dict['has_proof'] else None
                    team_dict['track_label'] = TRACK_NAMES.get(team_dict['track'], team_dict['track'])

                    members = db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()
                    actions = db.execute('SELECT * FROM admin_actions WHERE team_id = ? ORDER BY id DESC', (team_id,)).fetchall()
                    dispatches = db.execute('SELECT * FROM email_dispatches WHERE team_id = ? ORDER BY id DESC', (team_id,)).fetchall()

                    if members:
                        first_m = dict(members[0])
                        team_dict['email'] = first_m.get('email', '')
                        team_dict['phone'] = first_m.get('phone', '')
                        team_dict['college'] = first_m.get('college', '')

                return self.send_json(200, {
                    'team': team_dict,
                    'members': [dict(m) for m in members],
                    'admin_actions': [dict(a) for a in actions],
                    'email_dispatches': [dict(e) for e in dispatches]
                })

            # GET /api/admin/registrations/<id>/proof
            m_proof = re.match(r'^/api/admin/registrations/([a-zA-Z0-9_\-]+)/proof$', path)
            if m_proof:
                team_id = m_proof.group(1)
                with connect() as db:
                    team_row = db.execute('SELECT proof, proof_type, proof_path FROM teams WHERE id = ?', (team_id,)).fetchone()
                    if not team_row or (not team_row['proof'] and not team_row['proof_path']):
                        return self.send_json(404, {'error': 'No payment proof uploaded for this team.'})
                    
                    proof_data = None
                    ptype = team_row['proof_type'] or 'image/jpeg'
                    if team_row['proof_path'] and team_row['proof_path'].startswith('supabase://'):
                        res = fetch_proof_from_supabase(team_row['proof_path'])
                        if res:
                            proof_data, ptype = res
                    elif team_row['proof_path']:
                        p_file = ROOT / team_row['proof_path']
                        if p_file.is_file():
                            proof_data = p_file.read_bytes()
                    if not proof_data and team_row['proof']:
                        proof_data = team_row['proof']
                        if isinstance(proof_data, memoryview):
                            proof_data = bytes(proof_data)

                    if not proof_data:
                        return self.send_json(404, {'error': 'Proof file missing on server.'})

                    self.send_response(200)
                    self.send_header('Content-Type', ptype)
                    self.send_header('Content-Length', str(len(proof_data)))
                    self.send_header('Cache-Control', 'private, max-age=60')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(proof_data)
                    return

            # GET /api/admin/registrations/<id>/pdf or pass.pdf
            m_pdf = re.match(r'^/api/admin/registrations/([a-zA-Z0-9_\-]+)/(?:pdf|pass\.pdf)$', path)
            if m_pdf:
                team_id = m_pdf.group(1)
                with connect() as db:
                    team_row = db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone()
                    if not team_row:
                        return self.send_json(404, {'error': 'Registration record not found.'})
                    team_dict = dict(team_row)
                    members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]

                base_url = resolve_public_base_url(self.headers)
                pdf_bytes = generate_pass_pdf(team_dict, members, base_url=base_url)

                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                self.send_header('Content-Disposition', f'attachment; filename="SUPERNOVA_PASS_{team_dict["id"]}.pdf"')
                self.send_header('Content-Length', str(len(pdf_bytes)))
                self.send_header('Cache-Control', 'private, no-cache')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Expose-Headers', 'Content-Disposition')
                self.end_headers()
                self.wfile.write(pdf_bytes)
                return

            return self.send_json(404, {'error': 'Admin endpoint not found.'})

        # ---------------------------------------------------------
        # Static files & routing
        # ---------------------------------------------------------
        if path == '/favicon.ico':
            fav_path = ROOT / 'assets' / 'nova-avatar.png'
            if fav_path.is_file():
                raw = fav_path.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(raw)))
                self.send_header('Cache-Control', 'public, max-age=86400')
                self.end_headers()
                self.wfile.write(raw)
                return
            else:
                self.send_response(204)
                self.end_headers()
                return

        if path in ('', '/', '/index.html'):
            target_rel = 'index.html'
        elif path in ('/admin', '/admin/', '/admin.html'):
            target_rel = 'admin.html'
        elif path == '/supernova.html':
            target_rel = 'index.html'
        else:
            target_rel = path.lstrip('/')

        # Resolve target path: look inside frontend/ first, then fall back to ROOT
        target_path = None
        for base_dir in [FRONTEND_DIR, ROOT]:
            test_path = (base_dir / target_rel).resolve()
            try:
                test_path.relative_to(ROOT)
                if test_path.is_file():
                    target_path = test_path
                    break
            except ValueError:
                continue

        if not target_path or not target_path.is_file() or target_path.suffix in ('.db', '.sqlite', '.py', '.txt'):
            if target_path and target_path.suffix in ('.db', '.sqlite', '.py'):
                return self.send_error(403, 'Forbidden')
            return self.send_error(404, 'File Not Found')

        mime_types = {
            '.html': 'text/html; charset=utf-8',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.mp3': 'audio/mpeg',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.json': 'application/json; charset=utf-8',
            '.svg': 'image/svg+xml',
            '.txt': 'text/plain; charset=utf-8'
        }
        mime = mime_types.get(target_path.suffix.lower(), 'application/octet-stream')

        try:
            raw = target_path.read_bytes()
        except OSError:
            return self.send_error(404, 'File Not Found')

        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'public, max-age=3600' if mime.startswith(('image/', 'audio/')) else 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        path = urlsplit(self.path).path

        # ---------------------------------------------------------
        # API: Public Team Registration (Duo & Trio strictly)
        # ---------------------------------------------------------
        if path == '/api/registrations':
            try:
                d = self.read_json_body()

                # Track validation
                raw_track = str(d.get('track', '')).strip().lower()
                track = TRACK_MAP.get(raw_track)
                if not track or track not in CAPACITIES:
                    raise ValueError(f'Invalid track "{raw_track}". Select Web Debugging or AI/ML.')

                # Team Leader Name
                leader_name = str(d.get('leader_name') or d.get('team_name') or '').strip()
                team_name = str(d.get('team_name') or f"Team {leader_name}").strip()
                if not 2 <= len(leader_name) <= 100:
                    raise ValueError('Team leader full name must be between 2 and 100 characters.')

                # Email validation
                email = str(d.get('email', '')).strip().lower()
                if not email or len(email) > 254 or not re.fullmatch(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                    raise ValueError('A valid leader email address is required.')

                # Phone validation
                raw_phone = str(d.get('phone', '')).strip()
                phone = re.sub(r'[\s()\-]', '', raw_phone)
                if not re.fullmatch(r'^\+?[0-9]{10,15}$', phone):
                    raise ValueError('A valid 10 to 15 digit mobile phone number is required.')

                # College validation
                college = str(d.get('college', '')).strip()
                if not 2 <= len(college) <= 160:
                    raise ValueError('College / institution name must be between 2 and 160 characters.')

                # Team size validation: Strictly Duo (2) or Trio (3)
                try:
                    team_size = int(d.get('team_size', 2))
                except (ValueError, TypeError):
                    raise ValueError('Team size must be 2 (Duo) or 3 (Trio).')

                if team_size not in (2, 3):
                    raise ValueError('Supernova 2026 strictly admits Duo (2 hackers) or Trio (3 hackers) teams.')

                # Build clean member list: leader + additional members
                clean_members = [(leader_name, email, phone, college, 'leader')]
                incoming_members = d.get('members', [])

                needed_additional = team_size - 1
                if not isinstance(incoming_members, list) or len(incoming_members) < needed_additional:
                    raise ValueError(f'Please provide details for all {team_size} team members.')

                for i in range(needed_additional):
                    item = incoming_members[i]
                    if isinstance(item, dict):
                        m_name = str(item.get('name', '')).strip()
                        m_email = str(item.get('email', '')).strip().lower() or None
                        m_phone = str(item.get('phone', '')).strip() or None
                        m_college = str(item.get('college', '')).strip() or college
                    else:
                        m_name = str(item).strip()
                        m_email = None
                        m_phone = None
                        m_college = college

                    if not 2 <= len(m_name) <= 100:
                        raise ValueError(f'Member {i+2} full name must be between 2 and 100 characters.')

                    if m_email and (len(m_email) > 254 or not re.fullmatch(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', m_email)):
                        raise ValueError(f'Member {i+2} has an invalid email format.')

                    clean_members.append((m_name, m_email, m_phone, m_college, 'member'))

                # Check unique emails within submission
                submitted_emails = [m[1] for m in clean_members if m[1]]
                if len(submitted_emails) != len(set(submitted_emails)):
                    raise ValueError('Each team member must have a distinct email address.')

                # Mandatory competition terms and consent
                terms_accepted = d.get('terms_accepted', False)
                if terms_accepted is not True:
                    raise ValueError('You must accept the competition terms and telemetry guidelines.')
                internship_accepted = bool(d.get('internship_accepted', True))

            except ValueError as e:
                return self.send_json(400, {'error': str(e)})
            except Exception:
                return self.send_json(400, {'error': 'Invalid request payload. Please verify your team data.'})

            # Generate reference ID and secure ticket token
            rid = 'SN26-' + uuid.uuid4().hex[:10].upper()
            ticket_token = secrets.token_urlsafe(24)
            initial_status = 'Pending Verification (Fee ₹300 Due On-Site)'
            member_names_json = json.dumps([m[0] for m in clean_members])

            try:
                with connect() as db:
                    db.execute('BEGIN IMMEDIATE')

                    # Check duplicate email in database - if already registered, return existing registration status directly
                    existing_team_id = None
                    for m in clean_members:
                        if m[1]:
                            exists = db.execute('''
                                SELECT m.team_id 
                                FROM members m 
                                JOIN teams t ON t.id = m.team_id 
                                WHERE LOWER(m.email) = LOWER(?)
                                ORDER BY (CASE WHEN t.payment_status = 'PAID' AND t.verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, t.created_at DESC
                                LIMIT 1
                            ''', (m[1],)).fetchone()
                            if exists:
                                existing_team_id = exists['team_id']
                                break

                    if existing_team_id:
                        team = db.execute('''
                            SELECT id, team_name, leader_name, track, team_size, 
                                   payment_status, verification_status, ticket_status, ticket_token,
                                   rejection_reason, fee_amount, member_names, created_at, status,
                                   proof, proof_path, proof_type, transaction_id,
                                   payment_submitted_at, payment_reviewed_at, payment_review_notes
                            FROM teams WHERE id = ?
                        ''', (existing_team_id,)).fetchone()

                        if team:
                            members = db.execute('''
                                SELECT name, role, email, phone, college FROM members WHERE team_id = ? ORDER BY id ASC
                            ''', (team['id'],)).fetchall()
                            payload = build_ticket_payload(team, members, already_registered=True)
                            return self.send_json(200, payload)

                    # Track capacity check
                    count = db.execute('SELECT COUNT(*) FROM teams WHERE track = ?', (track,)).fetchone()[0]
                    if count >= CAPACITIES[track]:
                        track_label = TRACK_NAMES.get(track, track.upper())
                        return self.send_json(409, {
                            'error': f'{track_label} track is at full capacity ({CAPACITIES[track]}/{CAPACITIES[track]} slots claimed). Please select the other track.'
                        })

                    # Insert team
                    db.execute('''
                        INSERT INTO teams (
                            id, team_name, leader_name, track, team_size, devices,
                            transaction_id, proof, proof_type, status, payment_status,
                            verification_status, ticket_status, ticket_token, rejection_reason,
                            fee_amount, member_names, terms_accepted, internship_accepted
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rid, team_name, leader_name, track, team_size, 0,
                        None, None, None, initial_status, 'PENDING',
                        'PENDING_VERIFICATION', 'PENDING', ticket_token, None,
                        CONFIRMED_FEE_AMOUNT, member_names_json,
                        bool(terms_accepted), bool(internship_accepted)
                    ))

                    # Insert members
                    db.executemany('''
                        INSERT INTO members (team_id, name, email, phone, college, role)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', [(rid, m[0], m[1], m[2], m[3], m[4]) for m in clean_members])

                # Dispatch Event A: Registration Received notification
                base_url = resolve_public_base_url(self.headers)
                email_res = None
                try:
                    team_info = {
                        'id': rid,
                        'team_name': team_name,
                        'leader_name': leader_name,
                        'track': track,
                        'team_size': team_size,
                        'payment_status': 'PENDING',
                        'verification_status': 'PENDING_VERIFICATION',
                        'ticket_status': 'PENDING',
                        'fee_amount': CONFIRMED_FEE_AMOUNT,
                        'email': email,
                        'ticket_token': ticket_token,
                        'college': college
                    }
                    members_info = [{'name': m[0], 'email': m[1], 'phone': m[2], 'college': m[3], 'role': m[4]} for m in clean_members]
                    email_res = send_email_notification('REGISTRATION_RECEIVED', team_info, members_info, base_url=base_url)
                except Exception as email_err:
                    print(f"Non-blocking email dispatch error on registration: {email_err}")

                return self.send_json(201, {
                    'id': rid,
                    'ticket_token': ticket_token,
                    'leader_name': leader_name,
                    'team_name': team_name,
                    'email': email,
                    'track': TRACK_NAMES.get(track, track),
                    'track_key': track,
                    'team_size': team_size,
                    'members': [m[0] for m in clean_members],
                    'status': initial_status,
                    'payment_status': 'PENDING',
                    'verification_status': 'PENDING_VERIFICATION',
                    'ticket_status': 'PENDING',
                    'fee_amount': CONFIRMED_FEE_AMOUNT,
                    'fee_formatted': CONFIRMED_FEE_LABEL,
                    'fee': CONFIRMED_FEE_LABEL,
                    'email_dispatch': email_res
                })

            except (sqlite3.IntegrityError, IntegrityError):
                try:
                    with connect() as db:
                        for m in clean_members:
                            if m[1]:
                                row = db.execute('''
                                    SELECT m.team_id 
                                    FROM members m 
                                    JOIN teams t ON t.id = m.team_id 
                                    WHERE LOWER(m.email) = LOWER(?)
                                    ORDER BY (CASE WHEN t.payment_status = 'PAID' AND t.verification_status = 'VERIFIED' THEN 1 ELSE 0 END) DESC, t.created_at DESC
                                    LIMIT 1
                                ''', (m[1],)).fetchone()
                                if row:
                                    team = db.execute('SELECT * FROM teams WHERE id = ?', (row['team_id'],)).fetchone()
                                    if team:
                                        members = db.execute('SELECT name, role, email, phone, college FROM members WHERE team_id = ? ORDER BY id ASC', (team['id'],)).fetchall()
                                        return self.send_json(200, build_ticket_payload(team, members, already_registered=True))
                except Exception:
                    pass
                return self.send_json(409, {'error': 'A member email is already registered.'})
            except (sqlite3.Error, DatabaseError):
                return self.send_json(503, {'error': 'Could not save registration due to database error. Please retry.'})

        # ---------------------------------------------------------
        # API: Public Payment Proof Screenshot Upload
        # ---------------------------------------------------------
        m_proof_upload = re.match(r'^/api/registrations/([a-zA-Z0-9_\-]+)/payment-proof$', path)
        if m_proof_upload:
            team_id = m_proof_upload.group(1).strip()
            with connect() as db:
                team = db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone()
                if not team:
                    return self.send_json(404, {'error': 'Registration record not found for reference identifier.'})

            try:
                d = self.read_json_body()
                img_data_str = str(d.get('proof_base64') or d.get('image') or '').strip()
                txn_id = str(d.get('txn_id') or d.get('transaction_id') or '').strip() or None
                if not img_data_str:
                    return self.send_json(400, {'error': 'Payment screenshot image data is required.'})

                if ',' in img_data_str:
                    img_data_str = img_data_str.split(',', 1)[1]

                raw_bytes = base64.b64decode(img_data_str)
                is_valid, mime_type, ext, err_msg = validate_image_payload(raw_bytes, max_bytes=5 * 1024 * 1024)
                if not is_valid:
                    return self.send_json(400, {'error': err_msg})

                clean_team_id = re.sub(r'[^a-zA-Z0-9_\-]', '', team_id)
                ts = int(datetime.now(timezone.utc).timestamp())
                filename = f"{clean_team_id}_{ts}{ext}"

                # Upload to Supabase Storage if configured, otherwise store on local filesystem
                supa_path = upload_proof_to_supabase(filename, raw_bytes, mime_type)
                if supa_path:
                    rel_path = supa_path
                else:
                    file_path = PROOFS_DIR / filename
                    file_path.write_bytes(raw_bytes)
                    rel_path = f"uploads/proofs/{filename}"

                try:
                    with connect() as db:
                        prev_status = team['payment_status']
                        db.execute('''
                            UPDATE teams SET
                                proof = ?,
                                proof_type = ?,
                                proof_path = ?,
                                transaction_id = COALESCE(?, transaction_id),
                                payment_status = 'PENDING_REVIEW',
                                payment_submitted_at = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (raw_bytes, mime_type, rel_path, txn_id, team_id))

                        updated_team = dict(db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone())
                        members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]
                except (sqlite3.IntegrityError, IntegrityError) as ie:
                    if 'transaction_id' in str(ie):
                        return self.send_json(400, {'error': 'This transaction reference (UTR) has already been submitted by another team. Please verify your UTR.'})
                    raise

                log_admin_action(team_id, 'PARTICIPANT', 'SUBMIT_PAYMENT_PROOF', prev_status, 'PENDING_REVIEW', f"Txn: {txn_id or 'Screenshot uploaded'}")

                base_url = resolve_public_base_url(self.headers)
                try:
                    send_email_notification('PAYMENT_UPDATE', updated_team, members, extra={'notes': f'Payment screenshot received (Txn: {txn_id or "Attached screenshot"}). Verification pending by organizers.'}, base_url=base_url)
                except Exception as em_err:
                    print(f"Non-blocking email dispatch error on proof upload: {em_err}")

                return self.send_json(200, {
                    'message': 'Payment proof submitted successfully. Your payment is pending admin verification.',
                    'payment_status': 'PENDING_REVIEW',
                    'transaction_id': txn_id,
                    'has_proof': True,
                    'proof_url': f'/api/ticket/{team_id}/proof',
                    'submitted_at': datetime.now(timezone.utc).isoformat()
                })
            except (ValueError, binascii.Error) as val_err:
                return self.send_json(400, {'error': f'Invalid upload payload: {str(val_err)}'})
            except Exception as e:
                return self.send_json(500, {'error': f'Server error processing proof upload: {str(e)}'})

        # ---------------------------------------------------------
        # API: Admin Login
        # ---------------------------------------------------------
        if path == '/api/admin/login':
            try:
                d = self.read_json_body()
                username = str(d.get('username', '')).strip()
                password = str(d.get('password', '')).strip()

                valid_user = hmac.compare_digest(username.encode(), ADMIN_USERNAME.encode())
                valid_pass = hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode())

                if not (valid_user and valid_pass):
                    return self.send_json(401, {'error': 'Invalid administrator credentials.'})

                token, expires_at = create_admin_session(username)
                return self.send_json(200, {
                    'token': token,
                    'username': username,
                    'expires_at': expires_at,
                    'message': 'Admin authentication successful.'
                })
            except ValueError as e:
                return self.send_json(400, {'error': str(e)})

        # ---------------------------------------------------------
        # API: Admin Logout
        # ---------------------------------------------------------
        if path == '/api/admin/logout':
            token = self.get_auth_token()
            revoke_admin_session(token)
            return self.send_json(200, {'message': 'Admin session terminated.'})

        # ---------------------------------------------------------
        # API: Admin Organizer Payment QR Code Upload
        # ---------------------------------------------------------
        if path == '/api/admin/organizer-qr':
            token = self.get_auth_token()
            admin_user = verify_admin_session(token)
            if not admin_user:
                return self.send_json(401, {'error': 'Unauthorized: Admin authentication required.'})

            try:
                d = self.read_json_body()
                img_data_str = str(d.get('image', '')).strip()
                if not img_data_str:
                    return self.send_json(400, {'error': 'Payment QR image data is required.'})

                if ',' in img_data_str:
                    img_data_str = img_data_str.split(',', 1)[1]

                raw_bytes = base64.b64decode(img_data_str)
                is_valid, mime_type, ext, err_msg = validate_image_payload(raw_bytes, max_bytes=5 * 1024 * 1024)
                if not is_valid:
                    return self.send_json(400, {'error': err_msg})

                # Clean any older organizer_qr files in QR_DIR so only the latest remains
                for old_f in QR_DIR.glob('organizer_qr.*'):
                    try:
                        old_f.unlink()
                    except Exception:
                        pass

                target_file = QR_DIR / f"organizer_qr{ext}"
                target_file.write_bytes(raw_bytes)
                try:
                    (ROOT / 'assets' / f"organizer-qr{ext}").write_bytes(raw_bytes)
                    if ext != '.jpg':
                        (ROOT / 'assets' / 'organizer-qr.jpg').write_bytes(raw_bytes)
                except Exception:
                    pass

                log_admin_action('SYSTEM', admin_user, 'UPDATE_ORGANIZER_QR', 'ACTIVE', 'UPDATED', f"Type: {mime_type}")

                now_v = int(target_file.stat().st_mtime)
                return self.send_json(200, {
                    'message': 'Official organizer payment QR code updated successfully.',
                    'qr_url': f'/api/organizer-qr/image?v={now_v}',
                    'version': now_v
                })
            except Exception as e:
                return self.send_json(400, {'error': f'Failed to update payment QR code: {str(e)}'})

        # ---------------------------------------------------------
        # API: Admin Registration Management Actions
        # ---------------------------------------------------------
        if path.startswith('/api/admin/registrations/'):
            token = self.get_auth_token()
            admin_user = verify_admin_session(token)
            if not admin_user:
                return self.send_json(401, {'error': 'Unauthorized: Admin authentication required.'})

            # Match /api/admin/registrations/<id>/<action>
            m_act = re.match(r'^/api/admin/registrations/([a-zA-Z0-9_\-]+)/([a-z\-]+)$', path)
            if not m_act:
                return self.send_json(404, {'error': 'Action endpoint not found.'})

            team_id, action = m_act.groups()

            with connect() as db:
                team = db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone()
                if not team:
                    return self.send_json(404, {'error': 'Registration record not found.'})

            # Action 1: Verify / Approve Payment
            if action in ('verify-payment', 'approve-payment'):
                try:
                    d = self.read_json_body() if self.headers.get('Content-Length') else {}
                except Exception:
                    d = {}
                notes = str(d.get('notes', 'Payment confirmed by administrator')).strip()

                with connect() as db:
                    prev_status = team['payment_status']
                    is_verified = (team['verification_status'] == 'VERIFIED')
                    new_ticket_status = 'CONFIRMED' if is_verified else team['ticket_status']
                    new_status = 'Verified & Confirmed' if is_verified else 'Payment Approved (Awaiting Final Approval)'
                    
                    db.execute('''
                        UPDATE teams 
                        SET payment_status = 'PAID',
                            payment_reviewed_at = CURRENT_TIMESTAMP,
                            payment_review_notes = ?,
                            ticket_status = ?,
                            status = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (notes, new_ticket_status, new_status, team_id))

                    updated_team = dict(db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone())
                    members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]

                log_admin_action(team_id, admin_user, 'VERIFY_PAYMENT', prev_status, 'PAID', notes)
                
                base_url = resolve_public_base_url(self.headers)
                email_result = None
                try:
                    if is_verified:
                        email_result = send_email_notification('FINAL_CONFIRMATION', updated_team, members, base_url=base_url)
                    else:
                        email_result = send_email_notification('PAYMENT_UPDATE', updated_team, members, extra={'notes': notes}, base_url=base_url)
                except Exception as em_err:
                    print(f"Email dispatch error: {em_err}")

                return self.send_json(200, {
                    'message': f'Payment marked as PAID for team {team_id}.' + (' Pass is now confirmed!' if is_verified else ' Awaiting final organizer approval.'),
                    'payment_status': 'PAID',
                    'ticket_status': new_ticket_status,
                    'email_dispatch': email_result
                })

            # Action: Reject Payment
            elif action == 'reject-payment':
                try:
                    d = self.read_json_body() if self.headers.get('Content-Length') else {}
                except Exception:
                    d = {}
                reason = str(d.get('reason', d.get('notes', 'Payment proof rejected by administrator'))).strip()
                if not reason:
                    return self.send_json(400, {'error': 'A rejection reason is required to reject payment.'})

                with connect() as db:
                    prev_status = team['payment_status']
                    new_ticket_status = 'PENDING'
                    new_status = 'Payment Rejected (Resubmission Allowed)'

                    db.execute('''
                        UPDATE teams 
                        SET payment_status = 'REJECTED',
                            payment_reviewed_at = CURRENT_TIMESTAMP,
                            payment_review_notes = ?,
                            rejection_reason = ?,
                            ticket_status = ?,
                            status = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (reason, reason, new_ticket_status, new_status, team_id))

                    updated_team = dict(db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone())
                    members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]

                log_admin_action(team_id, admin_user, 'REJECT_PAYMENT', prev_status, 'REJECTED', f"Reason: {reason}")

                base_url = resolve_public_base_url(self.headers)
                email_result = None
                try:
                    email_result = send_email_notification('PAYMENT_UPDATE', updated_team, members, extra={'notes': f'Payment screenshot rejected: {reason}. Please log into SUPERNOVA and resubmit payment proof.'}, base_url=base_url)
                except Exception as em_err:
                    print(f"Email dispatch error: {em_err}")

                return self.send_json(200, {
                    'message': f'Payment rejected for team {team_id}. Participant can now re-upload proof.',
                    'payment_status': 'REJECTED',
                    'rejection_reason': reason,
                    'ticket_status': new_ticket_status,
                    'email_dispatch': email_result
                })

                base_url = resolve_public_base_url(self.headers)
                email_result = None
                try:
                    email_result = send_email_notification('PAYMENT_UPDATE', updated_team, members, extra={'notes': notes}, base_url=base_url)
                except Exception as em_err:
                    print(f"Email dispatch error: {em_err}")

                return self.send_json(200, {
                    'message': f'Payment revoked/marked pending for team {team_id}. Official pass locked.',
                    'payment_status': 'PENDING',
                    'ticket_status': new_ticket_status,
                    'email_dispatch': email_result
                })

            # Action 2: Approve Registration
            elif action == 'approve':
                try:
                    d = self.read_json_body() if self.headers.get('Content-Length') else {}
                except Exception:
                    d = {}
                notes = str(d.get('notes', 'Approved by administrator')).strip()

                with connect() as db:
                    prev_status = team['verification_status']
                    is_paid = (team['payment_status'] == 'PAID')
                    new_ticket_status = 'CONFIRMED' if is_paid else 'PENDING'
                    new_status = 'Verified & Confirmed' if is_paid else 'Approved (Pending Payment Check)'

                    db.execute('''
                        UPDATE teams 
                        SET verification_status = 'VERIFIED',
                            ticket_status = ?,
                            status = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_ticket_status, new_status, team_id))

                    updated_team = dict(db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone())
                    members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]

                log_admin_action(team_id, admin_user, 'APPROVE_REGISTRATION', prev_status, 'VERIFIED', notes)

                base_url = resolve_public_base_url(self.headers)
                email_result = None
                try:
                    if is_paid:
                        # Trigger confirmation email only if both conditions are met
                        email_result = send_email_notification('FINAL_CONFIRMATION', updated_team, members, base_url=base_url)
                    else:
                        email_result = send_email_notification('APPROVAL_STATUS', updated_team, members, extra={'notes': notes}, base_url=base_url)
                except Exception as em_err:
                    print(f"Email dispatch error: {em_err}")

                return self.send_json(200, {
                    'message': f'Registration {team_id} approved.' + (' Official ticket pass confirmed!' if is_paid else ' Official ticket will unlock upon payment verification.'),
                    'verification_status': 'VERIFIED',
                    'ticket_status': new_ticket_status,
                    'email_dispatch': email_result
                })

            # Action 3: Reject Registration
            elif action == 'reject':
                try:
                    d = self.read_json_body()
                    reason = str(d.get('reason', '')).strip()
                    if not reason:
                        raise ValueError('A rejection reason is required.')
                except ValueError as e:
                    return self.send_json(400, {'error': str(e)})

                with connect() as db:
                    prev_status = team['verification_status']
                    db.execute('''
                        UPDATE teams 
                        SET verification_status = 'REJECTED',
                            ticket_status = 'REVOKED',
                            status = 'Application Rejected',
                            rejection_reason = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (reason, team_id))

                    updated_team = dict(db.execute('SELECT * FROM teams WHERE id = ?', (team_id,)).fetchone())
                    members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]

                log_admin_action(team_id, admin_user, 'REJECT_REGISTRATION', prev_status, 'REJECTED', f"Reason: {reason}")

                base_url = resolve_public_base_url(self.headers)
                email_result = None
                try:
                    email_result = send_email_notification('APPROVAL_STATUS', updated_team, members, extra={'reason': reason}, base_url=base_url)
                except Exception as em_err:
                    print(f"Email dispatch error: {em_err}")

                return self.send_json(200, {
                    'message': f'Registration {team_id} has been rejected.',
                    'verification_status': 'REJECTED',
                    'ticket_status': 'REVOKED',
                    'rejection_reason': reason,
                    'email_dispatch': email_result
                })

            # Action 4: Resend Confirmation Email
            elif action == 'resend-email':
                with connect() as db:
                    updated_team = dict(team)
                    members = [dict(m) for m in db.execute('SELECT * FROM members WHERE team_id = ? ORDER BY id ASC', (team_id,)).fetchall()]

                base_url = resolve_public_base_url(self.headers)
                email_result = None
                try:
                    is_confirmed = (updated_team['payment_status'] == 'PAID' and updated_team['verification_status'] == 'VERIFIED')
                    if is_confirmed:
                        email_result = send_email_notification('FINAL_CONFIRMATION', updated_team, members, force_resend=True, base_url=base_url)
                    elif updated_team['verification_status'] == 'REJECTED':
                        email_result = send_email_notification('APPROVAL_STATUS', updated_team, members, extra={'reason': updated_team.get('rejection_reason', '')}, force_resend=True, base_url=base_url)
                    elif updated_team['verification_status'] == 'VERIFIED':
                        email_result = send_email_notification('APPROVAL_STATUS', updated_team, members, force_resend=True, base_url=base_url)
                    else:
                        email_result = send_email_notification('REGISTRATION_RECEIVED', updated_team, members, force_resend=True, base_url=base_url)
                except Exception as em_err:
                    email_result = {'status': 'FAILED', 'error': str(em_err)}

                log_admin_action(team_id, admin_user, 'RESEND_EMAIL', updated_team['verification_status'], updated_team['verification_status'], f"Recipient: {email_result.get('recipient')} | Status: {email_result.get('status')}")

                return self.send_json(200, {
                    'message': f'Email dispatch triggered for {team_id}. Status: {email_result.get("status")}',
                    'email_dispatch': email_result,
                    'dispatch': email_result
                })

            return self.send_json(404, {'error': 'Unknown admin action.'})

        return self.send_json(404, {'error': 'Endpoint not found.'})


def run_server():
    port = int(os.environ.get('PORT', sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    server_address = (host, port)

    # Initialize authoritative schema
    try:
        init_and_migrate_db()
    except Exception as e:
        print(f"[FATAL DB INIT ERROR] Could not initialize database schema: {e}")
        if get_database_url():
            print("[CRITICAL] DATABASE_URL is configured but connection failed. Exiting to prevent ephemeral fallback.")
            sys.exit(1)

    diag = get_database_diagnostics()
    print("=" * 72)
    print(" SUPERNOVA 2026 QUANTUM HACK - REGISTRATION SERVER")
    print(f" Authoritative Engine   : {diag['engine'].upper()} ({diag['driver']})")
    print(f" Persistence Tier       : {diag['persistence_tier']}")
    print(f" Database Endpoint      : {diag['sanitized_endpoint']}")
    print(f" Stored Registrations   : {diag['teams_count']} teams, {diag['members_count']} members")
    print(f" Verified / Paid Teams  : {diag['verified_count']} verified, {diag['paid_count']} paid")
    if diag['persistence_tier'] == 'UNSAFE_EPHEMERAL_CONTAINER':
        print("!" * 72)
        print(" [P0 PERSISTENCE WARNING] RUNNING ON EPHEMERAL DOCKER CONTAINER STORAGE!")
        print(" Container restarts will lose SQLite data! Set DATABASE_URL in Render.")
        print("!" * 72)
    print("=" * 72)

    httpd = ThreadingHTTPServer(server_address, Server)
    print(f'Server running on http://127.0.0.1:{port} (host: {host})')
    print(f'Admin Account: {ADMIN_USERNAME} | Password: {ADMIN_PASSWORD}')
    print('Press Ctrl+C to stop.')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down server.')
        httpd.server_close()

if __name__ == '__main__':
    run_server()
