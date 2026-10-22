import io
import os
import qrcode
from pathlib import Path
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
FRONTEND_DIR = ROOT / 'frontend'

TRACK_DISPLAY_NAMES = {
    'web': 'WEB DEBUGGING',
    'web_debugging': 'WEB DEBUGGING',
    'debugging': 'WEB DEBUGGING',
    'ai': 'AI / ML SYSTEM',
    'aiml': 'AI / ML SYSTEM',
    'ai_ml': 'AI / ML SYSTEM',
    'ai/ml': 'AI / ML SYSTEM'
}

def resolve_pass_base_url(base_url=None) -> str:
    """
    Returns the canonical routable public URL for QR codes.
    Falls back to official live production frontend if localhost or omitted.
    Scanning the QR code on the pass opens the live deployed homepage directly.
    """
    env_url = os.environ.get('FRONTEND_URL') or os.environ.get('PUBLIC_URL') or os.environ.get('APP_URL')
    if env_url:
        return env_url.rstrip('/')
    if base_url and 'localhost' not in base_url and '127.0.0.1' not in base_url:
        return base_url.rstrip('/')
    return "https://supernova-hackathon-frontend.vercel.app"

def find_template_path() -> Path:
    """
    Finds the high-fidelity cyberpunk master ticket template image.
    """
    candidates = [
        ROOT / 'assets' / 'ticket_base_template.png',
        BACKEND_DIR / 'ticket_base_template.png',
        BACKEND_DIR / 'assets' / 'ticket_base_template.png',
        FRONTEND_DIR / 'assets' / 'ticket_base_template.png',
        FRONTEND_DIR / 'ticket_base_template.png'
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None

def generate_pass_pdf(team, members, base_url=None) -> bytes:
    """
    Generates the official landscape SUPERNOVA QUANTUM HACK 2026 Ticket Pass as a vector PDF.
    Faithfully replicates the blueprint reference design:
    - 16:9 Landscape widescreen (1024x576)
    - High-fidelity cyberpunk neon frame & dark obsidian backdrop
    - Stylized metallic 3D SUPERNOVA title with lens flare star on 'A'
    - Tolani College & Dept. of Data Science & IT header branding
    - Cyberpunk Nova Mascot holding the glowing delta holographic icon
    - 3 Info cards: Date, Venue, and dynamic Selected Track
    - Team details panel: Team Name, Size (Duo/Trio), Lead Member, College, and Members roster
    - Coordinator & Convenor signatures with center motto
    - Right-side verification stub:
      * High-contrast scannable QR code opening the live deployed website
      * Dynamic Registration ID
      * 3-State dynamic status badge (VERIFIED / PENDING / REVOKED)
      * 3 Bottom event highlight chips (Rupee prize pool, Internships, Intensive schedule)
    """
    buf = io.BytesIO()
    width, height = 1024, 576
    c = canvas.Canvas(buf, pagesize=(width, height))
    
    # 1. Dynamic Data Extraction & Sanitization
    team_id = str(team.get('id', 'SN26-UNKNOWN')).strip()
    team_name = str(team.get('team_name') or team.get('leader_name') or 'Team Operatives').strip()
    leader_name = str(team.get('leader_name', members[0]['name'] if members else 'Lead Operative')).strip()
    
    raw_track = str(team.get('track', 'web')).lower().strip()
    track_display = TRACK_DISPLAY_NAMES.get(raw_track, 'AI / ML SYSTEM' if 'ai' in raw_track or 'ml' in raw_track else 'WEB DEBUGGING')
    
    team_size = int(team.get('team_size', len(members) or 2))
    size_label = '02 Members (Duo)' if team_size == 2 else '03 Members (Trio)'
    
    college = str(team.get('college') or (members[0].get('college') if members else '') or 'Tolani College of Commerce & Science').strip()

    c.setTitle(f"SUPERNOVA 2026 PASS // {team_id}")
    c.setAuthor("Tolani College of Commerce & Science - Dept of Data Science & IT")
    c.setSubject(f"Official Event Ticket Pass for {team_name} ({team_id})")

    # 2. Render Blueprint Base Template
    template_path = find_template_path()
    if template_path:
        c.drawImage(str(template_path), 0, 0, width=width, height=height)
    else:
        # Fallback procedural background if template is absent
        c.setFillColor(HexColor('#020717'))
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(HexColor('#051333'))
        c.circle(width * 0.42, height * 0.55, 260, fill=1, stroke=0)

    # 3. Dynamic Track Value (Card 3: x=468, y=576-279)
    c.setFillColor(HexColor('#FFFFFF'))
    c.setFont('Helvetica-Bold', 10.5)
    c.drawString(468, 576 - 279, track_display)

    # 4. Team Details Panel (Left Column)
    c.setFillColor(HexColor('#FFFFFF'))
    c.setFont('Helvetica-Bold', 8.5)
    c.drawString(226, 576 - 362, team_name[:26])
    c.drawString(226, 576 - 382, size_label)
    c.drawString(226, 576 - 402, leader_name[:26])
    c.setFont('Helvetica-Bold', 8)
    c.drawString(226, 576 - 422, college[:36])

    # 5. Team Details Panel (Right Column - Members Roster)
    m_list = members if members else [{'name': leader_name, 'role': 'leader'}]
    dy = 576 - 382
    for idx, m in enumerate(m_list[:3]):
        m_name = m.get('name', f"Member {idx+1}").strip()
        is_lead = (idx == 0 or m.get('role') == 'leader')
        
        c.setFillColor(HexColor('#00E5FF'))
        c.setFont('Helvetica-Bold', 8.5)
        c.drawString(490, dy, f"{idx+1}.")
        
        c.setFillColor(HexColor('#FFFFFF'))
        c.setFont('Helvetica-Bold', 8.5)
        c.drawString(510, dy, m_name[:22])
        
        if is_lead:
            c.setFillColor(HexColor('#38BDF8'))
            c.setFont('Helvetica-Bold', 8)
            c.drawString(620, dy, "(Lead)")
        dy -= 20

    # 6. Scannable High-Contrast QR Code (Right Verification Stub)
    try:
        target_base = resolve_pass_base_url(base_url)
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(target_base)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='black', back_color='white')
        
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format='PNG')
        qr_buf.seek(0)
        
        # Draw live QR code directly inside the white container box
        c.drawImage(ImageReader(qr_buf), 852, 576 - 240, 110, 110)
    except Exception as e:
        # Graceful fallback: render placeholder text if QR generation fails
        c.setFillColor(HexColor('#000000'))
        c.setFont('Helvetica', 8)
        c.drawCentredString(907, 576 - 185, "SUPERNOVA 2026")

    # 7. Registration ID
    c.setFillColor(HexColor('#FFFFFF'))
    c.setFont('Helvetica-Bold', 13.5)
    c.drawCentredString(907, 576 - 311, team_id)

    # 8. Canonical 3-State Status Badge
    # Matching production business rules:
    # 1. VERIFIED: Both payment PAID and verification VERIFIED, or CONFIRMED ticket status
    # 2. REVOKED: Either payment or verification REJECTED, or ticket REVOKED
    # 3. PENDING: Default awaiting verification
    p_status = str(team.get('payment_status', '')).upper().strip()
    v_status = str(team.get('verification_status', '')).upper().strip()
    t_status = str(team.get('ticket_status', '')).upper().strip()

    is_verified = (
        (p_status in ('PAID', 'COMPLETED') and v_status == 'VERIFIED') or 
        (t_status == 'CONFIRMED') or
        bool(team.get('is_eligible', False))
    )
    is_rejected = (
        p_status == 'REJECTED' or
        v_status == 'REJECTED' or
        t_status in ('REVOKED', 'REJECTED')
    )

    badge_x = 907 - 60
    badge_y = 576 - 370
    badge_w = 120
    badge_h = 24

    if is_verified:
        # Green VERIFIED Pill Badge
        c.setFillColor(HexColor('#032616'))
        c.setStrokeColor(HexColor('#22c55e'))
        c.setLineWidth(1.2)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 6, fill=1, stroke=1)

        # Checkmark Icon in Circle
        c.setFillColor(HexColor('#22c55e'))
        c.circle(badge_x + 22, badge_y + 12, 6, fill=1, stroke=0)
        c.setFillColor(HexColor('#032616'))
        c.circle(badge_x + 22, badge_y + 12, 4.5, fill=1, stroke=0)
        c.setStrokeColor(HexColor('#22c55e'))
        c.setLineWidth(1.2)
        p_chk = c.beginPath()
        p_chk.moveTo(badge_x + 19, badge_y + 12)
        p_chk.lineTo(badge_x + 21.5, badge_y + 9.5)
        p_chk.lineTo(badge_x + 25.5, badge_y + 14.5)
        c.drawPath(p_chk, fill=0, stroke=1)

        c.setFillColor(HexColor('#4ade80'))
        c.setFont('Helvetica-Bold', 9)
        c.drawString(badge_x + 36, badge_y + 8, "VERIFIED")

    elif is_rejected:
        # Red REVOKED Pill Badge
        c.setFillColor(HexColor('#2a080c'))
        c.setStrokeColor(HexColor('#ef4444'))
        c.setLineWidth(1.2)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 6, fill=1, stroke=1)

        # Cross Icon in Circle
        c.setFillColor(HexColor('#ef4444'))
        c.circle(badge_x + 22, badge_y + 12, 6, fill=1, stroke=0)
        c.setStrokeColor(HexColor('#2a080c'))
        c.setLineWidth(1.5)
        c.line(badge_x + 19, badge_y + 9, badge_x + 25, badge_y + 15)
        c.line(badge_x + 19, badge_y + 15, badge_x + 25, badge_y + 9)

        c.setFillColor(HexColor('#f87171'))
        c.setFont('Helvetica-Bold', 9)
        c.drawString(badge_x + 36, badge_y + 8, "REVOKED")

    else:
        # Amber PENDING Pill Badge
        c.setFillColor(HexColor('#2d1a04'))
        c.setStrokeColor(HexColor('#f59e0b'))
        c.setLineWidth(1.2)
        c.roundRect(badge_x, badge_y, badge_w, badge_h, 6, fill=1, stroke=1)

        # Clock / Hourglass Icon in Circle
        c.setFillColor(HexColor('#f59e0b'))
        c.circle(badge_x + 22, badge_y + 12, 6, fill=1, stroke=0)
        c.setStrokeColor(HexColor('#2d1a04'))
        c.setLineWidth(1.2)
        c.line(badge_x + 22, badge_y + 12, badge_x + 22, badge_y + 15)
        c.line(badge_x + 22, badge_y + 12, badge_x + 25, badge_y + 12)

        c.setFillColor(HexColor('#fbbf24'))
        c.setFont('Helvetica-Bold', 9)
        c.drawString(badge_x + 36, badge_y + 8, "PENDING")

    c.save()
    return buf.getvalue()
