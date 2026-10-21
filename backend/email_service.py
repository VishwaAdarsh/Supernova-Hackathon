import io
import os
import re
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from pathlib import Path

from pdf_generator import generate_pass_pdf, TRACK_DISPLAY_NAMES

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
DATABASE_DIR = ROOT / 'database'
DATABASE = (DATABASE_DIR / 'registrations.db') if (DATABASE_DIR / 'registrations.db').exists() else (ROOT / 'registrations.db')
DISPATCH_LOG = ROOT / 'email_dispatch_log.txt'

def load_dotenv(env_path=None, override=False):
    """Safely loads variables from .env into os.environ."""
    if env_path is None:
        env_path = ROOT / '.env'
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and (override or k not in os.environ):
                    os.environ[k] = v
    except Exception as e:
        print(f"Warning: could not load .env: {e}")

# Initial load of .env
load_dotenv()

def get_smtp_config():
    """Reads and validates SMTP configuration from environment variables."""
    # Ensure fresh .env variables are loaded
    load_dotenv(override=False)
    host = os.environ.get('SMTP_HOST', '').strip()
    try:
        port = int(os.environ.get('SMTP_PORT', '587').strip() or 587)
    except ValueError:
        port = 587
        
    username = os.environ.get('SMTP_USERNAME', os.environ.get('SMTP_USER', '')).strip()
    password = os.environ.get('SMTP_PASSWORD', os.environ.get('SMTP_PASS', '')).strip()
    if 'gmail' in host.lower() or len(password.replace(' ', '')) == 16:
        # Standardize 16-character Google App Passwords
        password = password.replace(' ', '')
    from_email = os.environ.get('SMTP_FROM_EMAIL', os.environ.get('SMTP_FROM', username or '')).strip()
    from_name = os.environ.get('SMTP_FROM_NAME', 'Arraman Swain (SUPERNOVA 2026)').strip() or 'Arraman Swain (SUPERNOVA 2026)'
    
    use_tls_raw = os.environ.get('SMTP_USE_TLS', 'true').strip().lower()
    use_ssl_raw = os.environ.get('SMTP_USE_SSL', 'false').strip().lower()
    use_tls = use_tls_raw in ('true', '1', 'yes')
    use_ssl = use_ssl_raw in ('true', '1', 'yes')

    is_configured = bool(host and from_email and (password or not username))

    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'from_email': from_email,
        'from_name': from_name,
        'use_tls': use_tls,
        'use_ssl': use_ssl,
        'is_configured': is_configured
    }

def is_valid_email(email):
    """Validates email format server-side."""
    if not email or not isinstance(email, str):
        return False
    return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email.strip()))

def get_email_styles():
    return """
    body { margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased; }
    .container { max-width: 600px; margin: 24px auto; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05); }
    .header { padding: 24px; background-color: #0c1527; border-bottom: 3px solid #2563eb; color: #ffffff; }
    .brand-title { color: #ffffff; font-size: 20px; font-weight: 800; letter-spacing: 0.5px; margin: 0; text-transform: uppercase; }
    .brand-subtitle { color: #60a5fa; font-size: 11px; font-weight: 600; letter-spacing: 1.5px; margin: 4px 0 0; text-transform: uppercase; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
    .content { padding: 28px 24px; color: #334155; }
    .salutation { font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }
    .lead-text { font-size: 14px; line-height: 1.6; color: #334155; margin-bottom: 18px; }
    .details-card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin: 18px 0; font-size: 13px; }
    .details-table { width: 100%; border-collapse: collapse; }
    .details-table td { padding: 7px 0; border-bottom: 1px solid #edf2f7; }
    .details-table tr:last-child td { border-bottom: none; }
    .detail-label { color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; width: 42%; }
    .detail-val { color: #0f172a; font-weight: 600; text-align: right; }
    .badge-confirmed { display: inline-block; padding: 3px 9px; background-color: #ecfdf5; border: 1px solid #10b981; color: #047857; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-pending { display: inline-block; padding: 3px 9px; background-color: #fffbeb; border: 1px solid #f59e0b; color: #b45309; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-rejected { display: inline-block; padding: 3px 9px; background-color: #fef2f2; border: 1px solid #ef4444; color: #b91c1c; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .schedule-box { background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 14px 16px; border-radius: 0 8px 8px 0; margin: 18px 0; font-size: 13px; line-height: 1.6; color: #1e3a8a; }
    .attachment-box { background-color: #f8fafc; border: 1px dashed #2563eb; border-radius: 8px; padding: 14px 16px; margin: 18px 0; text-align: center; }
    .footer { padding: 20px 24px; border-top: 1px solid #e2e8f0; background-color: #f8fafc; font-size: 11px; color: #64748b; line-height: 1.6; text-align: center; }
    """

def build_email_template(notification_type, team, members, extra=None, base_url="http://localhost:8000"):
    """
    Constructs clean, professional, high-deliverability subject, plain text, and HTML
    for all 4 notification types. Omits non-routable localhost links to avoid spam filters.
    """
    team_id = team.get('id', 'SN26-XXXXX')
    team_name = team.get('team_name') or team.get('leader_name') or 'Team'
    leader_name = team.get('leader_name', 'Participant')
    track_key = str(team.get('track', 'web')).lower()
    track_label = TRACK_DISPLAY_NAMES.get(track_key, track_key.upper())
    team_size = int(team.get('team_size', len(members) or 2))
    size_str = f"{team_size} Members ({'Duo' if team_size == 2 else 'Trio'})"
    college = team.get('college') or (members[0].get('college') if members else '') or 'Tolani College of Commerce & Science'

    # Check if a public website URL is configured for linking (omit localhost to prevent spam classification)
    public_base = os.environ.get('PUBLIC_WEB_URL', '').strip()
    is_valid_public = bool(public_base and not any(h in public_base.lower() for h in ['localhost', '127.0.0.1']))
    public_ticket_url = f"{public_base}/?ref={team_id}" if is_valid_public else None

    # Format member roster
    m_list = members if members else [{'name': leader_name, 'role': 'leader'}]
    roster_plain = []
    roster_html = []
    for idx, m in enumerate(m_list):
        role_label = 'Team Lead' if idx == 0 or m.get('role') == 'leader' else f'Member {idx+1}'
        m_name = m.get('name', 'N/A')
        m_email = m.get('email', '')
        roster_plain.append(f"  • {role_label}: {m_name} ({m_email})" if m_email else f"  • {role_label}: {m_name}")
        roster_html.append(f"<li style='margin-bottom: 5px; color: #334155;'><strong style='color:#0f172a;'>{m_name}</strong> <span style='color:#64748b;'>({role_label})</span></li>")

    roster_plain_str = "\n".join(roster_plain)
    roster_html_str = "".join(roster_html)

    clean_team_title = team_name if team_name.lower().startswith('team') else f"Team {team_name}"
    link_html = f'<div style="text-align: center; margin-top: 20px;"><a href="{public_ticket_url}" style="display:inline-block; background-color:#2563eb; color:#ffffff; padding:10px 22px; border-radius:6px; font-weight:600; text-decoration:none; font-size:13px;">View Registration Online</a></div>' if public_ticket_url else f'<div style="text-align: center; margin-top: 16px; font-size: 12px; color: #64748b;">Registration ID: <strong style="color: #2563eb;">{team_id}</strong></div>'
    link_plain = f"Registration Portal: {public_ticket_url}\n" if public_ticket_url else f"Registration Reference ID: {team_id}\n"

    # -------------------------------------------------------------
    # EVENT A: Registration Received
    # -------------------------------------------------------------
    if notification_type == 'REGISTRATION_RECEIVED':
        subject = f"SUPERNOVA 2026: Registration Received - {clean_team_title} ({team_id})"
        
        plain_text = f"""SUPERNOVA - Quantum Hack 2026: Registration Received
Tolani College of Commerce, Mumbai
=============================================================

Hi {leader_name},

Thank you for registering {clean_team_title} for SUPERNOVA - Quantum Hack 2026.
Your application details have been received and recorded in our event system.

REGISTRATION DETAILS:
-------------------------------------------------------------
Registration ID        : {team_id}
Team Name              : {team_name}
Assigned Track         : {track_label}
Team Size              : {size_str}
College / Institution  : {college}
Application Status     : Received (Under Review)

REGISTERED TEAM ROSTER:
{roster_plain_str}

EVENT SCHEDULE & VENUE:
-------------------------------------------------------------
Date      : Tuesday, 1 December 2026
Reporting : 07:30 AM - 08:30 AM IST (Registration Desk Check-In)
Kickoff   : 09:00 AM IST
Venue     : Tolani College of Commerce, 149-C, Sher-E-Punjab Society,
            Mahakali Caves Road, Andheri East, Mumbai, Maharashtra 400093.

NEXT STEPS:
Once your registration is verified by the organizing committee, your official ticket pass will be generated and emailed directly to your team.

{link_plain}
If you have any questions before the event, feel free to reply directly to this email.

Best regards,
Arraman Swain
SUPERNOVA 2026 Organizing Team
Tolani College of Commerce, Mumbai
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>{get_email_styles()}</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="brand-title">SUPERNOVA 2026</h1>
      <p class="brand-subtitle">Quantum Hack &bull; Tolani College, Mumbai</p>
    </div>
    <div class="content">
      <div class="salutation">Hi {leader_name},</div>
      <p class="lead-text">
        Thank you for registering <strong>{clean_team_title}</strong> for <strong>SUPERNOVA - Quantum Hack 2026</strong>.
        Your application has been successfully recorded in our event system.
      </p>

      <div class="details-card">
        <table class="details-table">
          <tr>
            <td class="detail-label">Registration ID:</td>
            <td class="detail-val" style="color: #2563eb;">{team_id}</td>
          </tr>
          <tr>
            <td class="detail-label">Team Name:</td>
            <td class="detail-val">{team_name}</td>
          </tr>
          <tr>
            <td class="detail-label">Assigned Track:</td>
            <td class="detail-val">{track_label}</td>
          </tr>
          <tr>
            <td class="detail-label">Team Quota:</td>
            <td class="detail-val">{size_str}</td>
          </tr>
          <tr>
            <td class="detail-label">Institution:</td>
            <td class="detail-val">{college}</td>
          </tr>
          <tr>
            <td class="detail-label">Status:</td>
            <td class="detail-val"><span class="badge-pending">Under Review</span></td>
          </tr>
        </table>
      </div>

      <div class="schedule-box">
        <strong style="color: #1e3a8a;">Event Schedule &amp; Venue:</strong><br>
        &bull; <strong>Date:</strong> Tuesday, 1 December 2026<br>
        &bull; <strong>Reporting:</strong> 07:30 AM IST (Registration Desk Check-in)<br>
        &bull; <strong>Venue:</strong> Tolani College of Commerce, Andheri East, Mumbai 400093
      </div>

      <p style="font-size: 13px; color: #475569; margin-bottom: 6px;"><strong>Registered Team Members:</strong></p>
      <ul style="font-size: 13px; padding-left: 20px; margin-top: 0;">
        {roster_html_str}
      </ul>

      {link_html}

      <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
        If you have any questions before the event, feel free to reply directly to this email.<br><br>
        Best regards,<br>
        <strong>Arraman Swain</strong><br>
        SUPERNOVA 2026 Organizing Team<br>
        Tolani College of Commerce, Mumbai
      </p>
    </div>
    <div class="footer">
      Organized by Department of Data Science &amp; Information Technology<br>
      Tolani College of Commerce, Andheri East, Mumbai · 400093
    </div>
  </div>
</body>
</html>
"""

    # -------------------------------------------------------------
    # EVENT B: Payment Status Update
    # -------------------------------------------------------------
    elif notification_type == 'PAYMENT_UPDATE':
        is_paid = (team.get('payment_status') == 'PAID')
        status_label = "Confirmed" if is_paid else "Under Review"
        subject = f"SUPERNOVA 2026: Registration Update - {clean_team_title} ({team_id})"

        plain_text = f"""SUPERNOVA - Quantum Hack 2026: Registration Update
Tolani College of Commerce, Mumbai
=============================================================

Hi {leader_name},

This is an update regarding your team registration for SUPERNOVA 2026.

REGISTRATION SUMMARY:
-------------------------------------------------------------
Registration ID        : {team_id}
Team Name              : {team_name}
Assigned Track         : {track_label}
Status                 : {status_label}

{'Your team registration submission has been verified by the organizing team. Once committee approval is complete, your official entry pass will be issued.' if is_paid else 'Your registration submission is currently under review by the organizers. You will receive an official confirmation pass as soon as review is complete.'}

{link_plain}
If you have any questions, feel free to reply directly to this email.

Best regards,
Arraman Swain
SUPERNOVA 2026 Organizing Team
Tolani College of Commerce, Mumbai
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>{get_email_styles()}</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="brand-title">SUPERNOVA 2026</h1>
      <p class="brand-subtitle">Registration Notification</p>
    </div>
    <div class="content">
      <div class="salutation">Hi {leader_name},</div>
      <p class="lead-text">
        This is an official update regarding your team registration for <strong>SUPERNOVA 2026</strong>.
      </p>

      <div class="details-card">
        <table class="details-table">
          <tr>
            <td class="detail-label">Registration ID:</td>
            <td class="detail-val" style="color: #2563eb;">{team_id}</td>
          </tr>
          <tr>
            <td class="detail-label">Team Name:</td>
            <td class="detail-val">{team_name}</td>
          </tr>
          <tr>
            <td class="detail-label">Status:</td>
            <td class="detail-val">
              <span class="{ 'badge-confirmed' if is_paid else 'badge-pending' }">{ status_label }</span>
            </td>
          </tr>
        </table>
      </div>

      <div class="schedule-box">
        { '<strong style="color: #047857;">Verification Complete:</strong> Your team details have been verified. Awaiting final organizer clearance to issue your official pass.' if is_paid else '<strong style="color: #b45309;">Under Review:</strong> Your submission is currently being reviewed by organizers. You will be notified as soon as it is processed.' }
      </div>

      {link_html}

      <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
        If you have any questions, feel free to reply directly to this email.<br><br>
        Best regards,<br>
        <strong>Arraman Swain</strong><br>
        SUPERNOVA 2026 Organizing Team<br>
        Tolani College of Commerce, Mumbai
      </p>
    </div>
    <div class="footer">
      Organized by Department of Data Science &amp; Information Technology<br>
      Tolani College of Commerce, Andheri East, Mumbai · 400093
    </div>
  </div>
</body>
</html>
"""

    # -------------------------------------------------------------
    # EVENT C: Registration Approval / Rejection
    # -------------------------------------------------------------
    elif notification_type == 'APPROVAL_STATUS':
        is_approved = (team.get('verification_status') == 'VERIFIED')
        rejection_reason = team.get('rejection_reason') or (extra.get('reason') if extra else '') or "Application criteria not satisfied"
        status_word = "Approved" if is_approved else "Update"
        subject = f"SUPERNOVA 2026: Registration {status_word} - {clean_team_title} ({team_id})"

        plain_text = f"""SUPERNOVA - Quantum Hack 2026: Registration Status
Tolani College of Commerce, Mumbai
=============================================================

Hi {leader_name},

This is an update regarding your team registration for SUPERNOVA 2026.

APPLICATION DECISION:
-------------------------------------------------------------
Registration ID        : {team_id}
Team Name              : {team_name}
Assigned Track         : {track_label}
Decision               : {'Approved by Committee' if is_approved else 'Application Not Approved'}
{f'Notes / Reason       : {rejection_reason}' if not is_approved else ''}

{'Congratulations! Your team registration has been reviewed and approved by the technical committee. Your official ticket pass will be issued once check-in verification is finalized.' if is_approved else 'We regret to inform you that your registration could not be approved for this edition of SUPERNOVA.'}

{link_plain}
If you have any questions, feel free to reply directly to this email.

Best regards,
Arraman Swain
SUPERNOVA 2026 Organizing Team
Tolani College of Commerce, Mumbai
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>{get_email_styles()}</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="brand-title">SUPERNOVA 2026</h1>
      <p class="brand-subtitle">Application Status Notification</p>
    </div>
    <div class="content">
      <div class="salutation">Hi {leader_name},</div>
      <p class="lead-text">
        An official evaluation decision has been issued for team <strong>{team_name}</strong>.
      </p>

      <div class="details-card">
        <table class="details-table">
          <tr>
            <td class="detail-label">Registration ID:</td>
            <td class="detail-val" style="color: #2563eb;">{team_id}</td>
          </tr>
          <tr>
            <td class="detail-label">Decision:</td>
            <td class="detail-val">
              <span class="{ 'badge-confirmed' if is_approved else 'badge-rejected' }">{ 'Approved' if is_approved else 'Not Approved' }</span>
            </td>
          </tr>
          { f'<tr><td class="detail-label">Notes:</td><td class="detail-val" style="color: #b91c1c;">{rejection_reason}</td></tr>' if not is_approved else '' }
        </table>
      </div>

      <div class="schedule-box">
        { '<strong style="color: #047857;">Application Approved:</strong> Your roster has passed technical evaluation. An official ticket pass will be confirmed once check-in verification is finalized.' if is_approved else '<strong style="color: #b91c1c;">Application Update:</strong> Your registration was not approved based on the notes above. For queries, please contact the organizing desk.' }
      </div>

      {link_html}

      <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
        If you have any questions, feel free to reply directly to this email.<br><br>
        Best regards,<br>
        <strong>Arraman Swain</strong><br>
        SUPERNOVA 2026 Organizing Team<br>
        Tolani College of Commerce, Mumbai
      </p>
    </div>
    <div class="footer">
      Organized by Department of Data Science &amp; Information Technology<br>
      Tolani College of Commerce, Andheri East, Mumbai · 400093
    </div>
  </div>
</body>
</html>
"""

    # -------------------------------------------------------------
    # EVENT D: Final Confirmation + Official Pass
    # -------------------------------------------------------------
    else:  # FINAL_CONFIRMATION
        subject = f"SUPERNOVA 2026: Entry Pass for {clean_team_title} ({team_id})"

        plain_text = f"""SUPERNOVA - Quantum Hack 2026: Official Entry Pass
Tolani College of Commerce, Mumbai
=============================================================

Hi {leader_name},

Your team registration for SUPERNOVA - Quantum Hack 2026 is officially confirmed!

Your official event pass has been generated and is attached to this email as a PDF (SUPERNOVA_PASS_{team_id}.pdf).

CONFIRMED TEAM DETAILS:
-------------------------------------------------------------
Registration ID        : {team_id}
Team Name              : {team_name}
Lead Participant       : {leader_name}
Assigned Track         : {track_label}
Team Size              : {size_str}
Institution            : {college}
Status                 : Confirmed & Pass Issued

CONFIRMED TEAM ROSTER:
{roster_plain_str}

EVENT SCHEDULE & VENUE DETAILS:
-------------------------------------------------------------
Date      : Tuesday, 1 December 2026
Reporting : 07:30 AM - 08:30 AM IST (Registration Desk Check-in)
Kickoff   : 09:00 AM IST
Concludes : 04:30 PM IST (Judging & Award Ceremony)
Venue     : Tolani College of Commerce, 149-C, Sher-E-Punjab Society,
            Mahakali Caves Road, Andheri East, Mumbai, Maharashtra 400093.

ATTACHED PASS INSTRUCTIONS:
Please open or save the attached "SUPERNOVA_PASS_{team_id}.pdf" on your phone.
Present your scannable QR code at the check-in desk on event morning for badge pickup.

{link_plain}
If you have any questions before the event, feel free to reply directly to this email.

Best regards,
Arraman Swain
SUPERNOVA 2026 Organizing Team
Tolani College of Commerce, Mumbai
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>{get_email_styles()}</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1 class="brand-title">SUPERNOVA 2026</h1>
      <p class="brand-subtitle">Quantum Hack &bull; Tolani College, Mumbai</p>
    </div>
    <div class="content">
      <div style="background-color: #ecfdf5; border: 1px solid #10b981; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 20px;">
        <span style="color: #047857; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
          Registration Confirmed &bull; Official Ticket Pass Issued
        </span>
      </div>

      <div class="salutation">Hi <strong>{leader_name}</strong>,</div>
      <p class="lead-text">
        Your team registration for <strong>SUPERNOVA - Quantum Hack 2026</strong> is officially confirmed!
        Your official event pass has been generated and is attached to this email as a PDF.
      </p>

      <div class="details-card">
        <table class="details-table">
          <tr>
            <td class="detail-label">Registration ID:</td>
            <td class="detail-val" style="color: #2563eb;">{team_id}</td>
          </tr>
          <tr>
            <td class="detail-label">Team Name:</td>
            <td class="detail-val">{team_name}</td>
          </tr>
          <tr>
            <td class="detail-label">Lead Participant:</td>
            <td class="detail-val">{leader_name}</td>
          </tr>
          <tr>
            <td class="detail-label">Assigned Track:</td>
            <td class="detail-val" style="color: #2563eb;">{track_label}</td>
          </tr>
          <tr>
            <td class="detail-label">Team Size:</td>
            <td class="detail-val">{size_str}</td>
          </tr>
          <tr>
            <td class="detail-label">Institution:</td>
            <td class="detail-val">{college}</td>
          </tr>
          <tr>
            <td class="detail-label">Status:</td>
            <td class="detail-val"><span class="badge-confirmed">Confirmed</span></td>
          </tr>
        </table>
      </div>

      <p style="font-size: 13px; color: #475569; margin-bottom: 6px;"><strong>Confirmed Team Roster:</strong></p>
      <ul style="font-size: 13px; padding-left: 20px; margin-top: 0;">
        {roster_html_str}
      </ul>

      <div class="schedule-box">
        <strong style="color: #1e3a8a;">Reporting &amp; Venue Details:</strong><br>
        &bull; <strong>Event Date:</strong> Tuesday, 1 December 2026<br>
        &bull; <strong>Reporting Window:</strong> 07:30 AM - 08:30 AM IST (Check-in &amp; Kit Pickup)<br>
        &bull; <strong>Event Kickoff:</strong> 09:00 AM IST<br>
        &bull; <strong>Venue:</strong> Tolani College of Commerce, 149-C, Sher-E-Punjab Society, Mahakali Caves Road, Andheri East, Mumbai, Maharashtra 400093.
      </div>

      <div class="attachment-box">
        <span style="color: #0f172a; font-size: 13px; font-weight: 700; display: block; margin-bottom: 4px;">
          Attached Official Pass: SUPERNOVA_PASS_{team_id}.pdf
        </span>
        <span style="color: #64748b; font-size: 12px;">
          Please open or save the attached vector PDF pass on your phone and present its scannable QR code at the check-in gate.
        </span>
      </div>

      {link_html}

      <p style="font-size: 13px; color: #64748b; margin-top: 24px;">
        If you have any questions before the event, feel free to reply directly to this email.<br><br>
        Best regards,<br>
        <strong>Arraman Swain</strong><br>
        SUPERNOVA 2026 Organizing Team<br>
        Tolani College of Commerce, Mumbai
      </p>
    </div>
    <div class="footer">
      Organized by Department of Data Science &amp; Information Technology<br>
      Tolani College of Commerce, Andheri East, Mumbai · 400093
    </div>
  </div>
</body>
</html>
"""

    return subject, plain_text, html_body


def send_email_notification(notification_type, team, members, extra=None, force_resend=False, base_url="http://localhost:8000"):
    """
    Core notification engine supporting all 4 event types with reliable logging,
    strict duplicate prevention for final confirmation emails, and real SMTP transmission.
    """
    recipient_email = team.get('email')
    if not recipient_email and members:
        recipient_email = members[0].get('email')

    if not is_valid_email(recipient_email):
        return {
            'status': 'FAILED',
            'notification_type': notification_type,
            'recipient': recipient_email or 'None',
            'error': f'Invalid recipient email address: "{recipient_email}"'
        }

    team_id = team.get('id', 'UNKNOWN')

    # Strict Dual-Condition Check for Final Confirmation
    if notification_type == 'FINAL_CONFIRMATION':
        is_paid = (team.get('payment_status') == 'PAID')
        is_verified = (team.get('verification_status') == 'VERIFIED')
        if not (is_paid and is_verified):
            return {
                'status': 'BLOCKED',
                'notification_type': notification_type,
                'recipient': recipient_email,
                'error': 'Final confirmation blocked: Pass requires BOTH payment_status == PAID and verification_status == VERIFIED.'
            }

        # Prevent duplicate final confirmation emails unless explicitly forced by admin
        if not force_resend:
            try:
                from database import connect
                with connect() as conn:
                    already_sent = conn.execute('''
                        SELECT id, sent_at FROM email_dispatches
                        WHERE team_id = ? AND notification_type = 'FINAL_CONFIRMATION' AND status = 'SENT'
                    ''', (team_id,)).fetchone()
                    if already_sent:
                        return {
                            'status': 'DUPLICATE_SKIPPED',
                            'notification_type': notification_type,
                            'recipient': recipient_email,
                            'error': f'Final confirmation email was already successfully sent at {already_sent["sent_at"]}. Skipped duplicate.'
                        }
            except Exception:
                pass

    # Build content
    subject, text_body, html_body = build_email_template(notification_type, team, members, extra, base_url)

    # Generate PDF pass if final confirmation
    pdf_bytes = None
    if notification_type == 'FINAL_CONFIRMATION':
        try:
            pdf_bytes = generate_pass_pdf(team, members, base_url)
        except Exception as e:
            print(f"Error generating pass PDF for {team_id}: {e}")

    # Build modern EmailMessage with RFC 5322 and RFC 2046 compliant structure
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)

    cfg = get_smtp_config()
    from_name = cfg['from_name'] or 'Arraman Swain (SUPERNOVA 2026)'
    from_email = cfg['from_email'] or 'swainarraman51@gmail.com'
    msg['From'] = formataddr((from_name, from_email))
    msg['To'] = recipient_email
    msg['Reply-To'] = from_email

    # Plain text content first (defaults to clean 7bit/quoted-printable encoding, avoiding BASE64_PLAIN spam triggers)
    msg.set_content(text_body)

    # Rich HTML content alternative second
    msg.add_alternative(html_body, subtype='html')

    # Attach PDF pass if generated (automatically promotes container to multipart/mixed)
    if pdf_bytes:
        msg.add_attachment(
            pdf_bytes,
            maintype='application',
            subtype='pdf',
            filename=f"SUPERNOVA_PASS_{team_id}.pdf"
        )

    # SMTP Transmission or Honest NOT_CONFIGURED state
    status = 'NOT_CONFIGURED'
    err_msg = None

    if not cfg['is_configured']:
        err_msg = 'SMTP environment variables not configured. Dispatch logged locally.'
    elif cfg['use_tls'] and cfg['use_ssl']:
        status = 'CONFIG_ERROR'
        err_msg = 'Incompatible configuration: both SMTP_USE_TLS and SMTP_USE_SSL cannot be enabled simultaneously.'
    else:
        server = None
        try:
            if cfg['use_ssl']:
                server = smtplib.SMTP_SSL(cfg['host'], cfg['port'], timeout=30)
            else:
                server = smtplib.SMTP(cfg['host'], cfg['port'], timeout=30)
                if cfg['use_tls']:
                    server.starttls()

            if cfg['username'] and cfg['password']:
                server.login(cfg['username'], cfg['password'])
            server.send_message(msg)

            status = 'SENT'
        except smtplib.SMTPAuthenticationError as e:
            status = 'AUTH_FAILED'
            err_msg = f"SMTP Authentication failed for user {cfg['username']}."
        except smtplib.SMTPException as e:
            status = 'FAILED'
            err_msg = f"SMTP protocol error: {str(e)}"
        except Exception as e:
            status = 'FAILED'
            err_msg = f"Connection error: {str(e)}"
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
                        pass

    # Record in database table email_dispatches
    try:
        from database import connect
        with connect() as conn:
            conn.execute('''
                INSERT INTO email_dispatches (team_id, recipient_email, subject, notification_type, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (team_id, recipient_email, subject, notification_type, status, err_msg))
    except Exception as e:
        print(f"Error logging dispatch to database: {e}")

    # Record in human-readable log file
    try:
        with open(DISPATCH_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n--- DISPATCH {datetime.now(timezone.utc).isoformat()} [{notification_type}] ---\n")
            f.write(f"To: {recipient_email} | Status: {status} | Ref: {team_id}\n")
            if err_msg:
                f.write(f"Note: {err_msg}\n")
            f.write(text_body)
            if pdf_bytes:
                f.write(f"\n[Attached: SUPERNOVA_PASS_{team_id}.pdf ({len(pdf_bytes)} bytes)]\n")
            f.write("\n" + ("=" * 55) + "\n")
    except Exception:
        pass

    return {
        'status': status,
        'notification_type': notification_type,
        'recipient': recipient_email,
        'error': err_msg,
        'has_pdf': bool(pdf_bytes)
    }
