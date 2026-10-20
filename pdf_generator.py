import io
import os
import qrcode
from pathlib import Path
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent

TRACK_DISPLAY_NAMES = {
    'web': 'Web Debugging',
    'web_debugging': 'Web Debugging',
    'ai': 'AI / ML System',
    'aiml': 'AI / ML System',
    'ai_ml': 'AI / ML System'
}

def generate_pass_pdf(team, members, base_url="http://localhost:8000") -> bytes:
    """
    Generates the official landscape SUPERNOVA 2026 Ticket Pass as a vector PDF.
    Matches the exact 1000x562 widescreen layout, cyan/electric blue neon palette,
    branding, 3 info cards, team details panel, signatures, and right verification stub.
    """
    buf = io.BytesIO()
    width, height = 1000, 562
    c = canvas.Canvas(buf, pagesize=(width, height))
    
    team_id = str(team.get('id', 'SN26-UNKNOWN'))
    team_name = str(team.get('team_name') or team.get('leader_name') or 'Team Operatives')
    leader_name = str(team.get('leader_name', 'Lead Operative'))
    track_key = str(team.get('track', 'web')).lower()
    track_label = TRACK_DISPLAY_NAMES.get(track_key, track_key.upper())
    team_size = int(team.get('team_size', len(members) or 2))
    size_label = '02 Members (Duo)' if team_size == 2 else '03 Members (Trio)'
    
    college = str(team.get('college') or (members[0].get('college') if members else '') or 'Tolani College of Commerce & Science')

    c.setTitle(f"SUPERNOVA 2026 PASS // {team_id}")
    c.setAuthor("Tolani College of Commerce & Science - Dept of Data Science & IT")
    c.setSubject(f"Official Event Ticket Pass for {team_name} ({team_id})")

    # --- 1. Background Fill ---
    c.setFillColor(HexColor('#020717'))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Subtle radial glow imitation (layered dark deep blue circles)
    c.setFillColor(HexColor('#051333'))
    c.circle(420, 320, 260, fill=1, stroke=0)
    c.setFillColor(HexColor('#030b20'))
    c.circle(420, 320, 180, fill=1, stroke=0)

    # --- 2. Outer Chamfered Cyber Frame ---
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(2)
    
    # Outer chamfered polygon with tear notches at x=780
    p = c.beginPath()
    p.moveTo(32, 10)
    p.lineTo(768, 10)
    # Top tear notch arc
    p.arc(768, 0, 792, 24, 180, -180)
    p.lineTo(968, 10)
    p.lineTo(990, 32)
    # Right edge with tech notches
    p.lineTo(990, 170)
    p.lineTo(995, 170)
    p.lineTo(995, 185)
    p.lineTo(990, 185)
    p.lineTo(990, 375)
    p.lineTo(995, 375)
    p.lineTo(995, 390)
    p.lineTo(990, 390)
    p.lineTo(990, 530)
    p.lineTo(968, 552)
    p.lineTo(792, 552)
    # Bottom tear notch arc
    p.arc(768, 538, 792, 562, 0, -180)
    p.lineTo(32, 552)
    p.lineTo(10, 530)
    # Left edge with tech notches
    p.lineTo(10, 390)
    p.lineTo(5, 390)
    p.lineTo(5, 375)
    p.lineTo(10, 375)
    p.lineTo(10, 185)
    p.lineTo(5, 185)
    p.lineTo(5, 170)
    p.lineTo(10, 170)
    p.lineTo(10, 32)
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    # Inner Concentric Cyber Line
    c.setStrokeColor(HexColor('#00E5FF'))
    c.setLineWidth(0.8)
    p_in = c.beginPath()
    p_in.moveTo(36, 16)
    p_in.lineTo(764, 16)
    p_in.lineTo(796, 16)
    p_in.lineTo(964, 16)
    p_in.lineTo(984, 36)
    p_in.lineTo(984, 526)
    p_in.lineTo(964, 546)
    p_in.lineTo(796, 546)
    p_in.lineTo(764, 546)
    p_in.lineTo(36, 546)
    p_in.lineTo(16, 526)
    p_in.lineTo(16, 36)
    p_in.close()
    c.drawPath(p_in, fill=0, stroke=1)

    # Corner Sci-Fi Accent Brackets
    c.setStrokeColor(HexColor('#00E5FF'))
    c.setLineWidth(1.5)
    # Top-Left
    c.line(8, 44, 8, 26)
    c.line(8, 26, 26, 8)
    c.line(26, 8, 44, 8)
    # Top-Right
    c.line(956, 8, 974, 8)
    c.line(974, 8, 992, 26)
    c.line(992, 26, 992, 44)
    # Bottom-Left
    c.line(8, 518, 8, 536)
    c.line(8, 536, 26, 554)
    c.line(26, 554, 44, 554)
    # Bottom-Right
    c.line(956, 554, 974, 554)
    c.line(974, 554, 992, 536)
    c.line(992, 536, 992, 518)

    # Top/Bottom Tech Accent Rects
    c.setFillColor(HexColor('#00E5FF'))
    c.rect(230, height - 13, 30, 3, fill=1, stroke=0)
    c.rect(850, height - 13, 25, 3, fill=1, stroke=0)
    c.rect(230, 10, 30, 3, fill=1, stroke=0)
    c.rect(850, 10, 25, 3, fill=1, stroke=0)

    # Perforated Vertical Tear Line
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1.5)
    c.setDash([5, 5])
    c.line(780, 20, 780, height - 20)
    c.setDash()

    # --- 3. LEFT SECTION: Header Bar ---
    # Tolani College Logo
    logo_path = ROOT / 'tolani-logo.jpg'
    if logo_path.is_file():
        try:
            c.setFillColor(HexColor('#ffffff'))
            c.roundRect(44, height - 60, 44, 44, 8, fill=1, stroke=0)
            c.setStrokeColor(HexColor('#00E5FF'))
            c.setLineWidth(1)
            c.roundRect(44, height - 60, 44, 44, 8, fill=0, stroke=1)
            c.drawImage(str(logo_path), 46, height - 58, 40, 40, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 13)
    c.drawString(98, height - 32, "TOLANI COLLEGE")

    c.setFillColor(HexColor('#38BDF8'))
    c.setFont('Helvetica', 8.5)
    c.drawString(98, height - 44, "DEPARTMENT OF DATA SCIENCE & IT")
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 9)
    c.drawString(274, height - 44, "////")

    c.setFillColor(HexColor('#7dd3fc'))
    c.setFont('Helvetica', 7.5)
    c.drawString(98, height - 55, "PRESENTS")

    # Header Right
    c.setFillColor(HexColor('#00A3FF'))
    c.setFont('Helvetica-Bold', 8)
    c.drawRightString(760, height - 32, "HACK // LEARN // BUILD // CONNECT")
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 9.5)
    c.drawRightString(760, height - 46, "THINK BEYOND. BUILD FEARLESSLY.")

    # Header divider
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(0.8)
    c.line(44, height - 68, 760, height - 68)

    # --- 4. Hero Title Area & HUD Line ---
    # HUD Sci-Fi Line Framing Supernova
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1.2)
    p_hud = c.beginPath()
    p_hud.moveTo(44, height - 94)
    p_hud.lineTo(360, height - 94)
    p_hud.lineTo(372, height - 82)
    p_hud.lineTo(425, height - 82)
    p_hud.lineTo(437, height - 94)
    p_hud.lineTo(530, height - 94)
    p_hud.lineTo(530, height - 100)
    c.drawPath(p_hud, fill=0, stroke=1)

    # Binary code stream (subtle vertical text behind mascot)
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Courier', 6.5)
    matrix_lines = [
        "01001011.10001000",
        ".100010000100001.",
        ".1000100011101111",
        ".010001110000101.",
        "01000111000010100",
        "10000100100000001",
        "01000000110000110",
        "10000110100001100",
        "01000100010010001",
        "10000011010001011",
        "01000001100001001",
        "01001101100000100"
    ]
    my = height - 85
    for mline in matrix_lines:
        c.drawString(560, my, mline)
        my -= 9

    # SUPERNOVA Title
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 38)
    c.drawString(44, height - 132, "SUPERNOVA")

    # Glowing Cyan Star Flare ✦ at apex of "A"
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 26)
    c.drawString(340, height - 120, "✦")

    # QUANTUM HACK 2026 Subtitle
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 17)
    c.drawString(44, height - 156, "QUANTUM HACK 2026")

    # Tagline
    c.setFillColor(HexColor('#00A3FF'))
    c.setFont('Helvetica-Bold', 8)
    c.drawString(44, height - 172, "HACKATHON // INNOVATION // REAL IMPACT")

    # Cyber Mascot Artwork (assets/nova-avatar.png)
    avatar_path = ROOT / 'assets' / 'nova-avatar.png'
    if avatar_path.is_file():
        try:
            c.drawImage(str(avatar_path), 545, height - 325, 230, 250, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # --- 5. Three Info Cards (Date, Venue, Track) ---
    pills = [
        ("DATE", "1 DECEMBER 2026", "07:30 AM IST", 44),
        ("VENUE", "TOLANI COLLEGE", "MUMBAI, INDIA", 226),
        ("TRACK", track_label.upper(), "SELECTED TRACK", 408)
    ]
    pill_w = 170
    pill_h = 44
    pill_y = height - 232

    for label, val1, val2, px in pills:
        # Card Background
        c.setFillColor(HexColor('#061433'))
        c.setStrokeColor(HexColor('#00A3FF'))
        c.setLineWidth(1)
        c.roundRect(px, pill_y, pill_w, pill_h, 8, fill=1, stroke=1)

        # Left Icon Box
        c.setFillColor(HexColor('#0a2048'))
        c.setStrokeColor(HexColor('#00E5FF'))
        c.setLineWidth(0.8)
        c.roundRect(px + 8, pill_y + 7, 30, 30, 6, fill=1, stroke=1)

        # Icon Symbol
        c.setFillColor(HexColor('#00E5FF'))
        c.setFont('Helvetica-Bold', 12)
        if label == "DATE":
            c.drawString(px + 17, pill_y + 17, "D")
        elif label == "VENUE":
            c.drawString(px + 18, pill_y + 17, "V")
        else:
            c.drawString(px + 14, pill_y + 17, "</>")

        # Label & Values
        c.setFillColor(HexColor('#38BDF8'))
        c.setFont('Helvetica-Bold', 7)
        c.drawString(px + 45, pill_y + 30, label)

        c.setFillColor(HexColor('#ffffff') if label != "TRACK" else HexColor('#00E5FF'))
        c.setFont('Helvetica-Bold', 9.5)
        c.drawString(px + 45, pill_y + 18, val1[:16])

        c.setFillColor(HexColor('#00A3FF') if label == "DATE" else HexColor('#94a3b8'))
        c.setFont('Helvetica', 7)
        c.drawString(px + 45, pill_y + 8, val2)

    # --- 6. Team Details Panel (2 Columns) ---
    box_x = 44
    box_y = height - 370
    box_w = 716
    box_h = 126

    c.setFillColor(HexColor('#050f26'))
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1)
    c.roundRect(box_x, box_y, box_w, box_h, 10, fill=1, stroke=1)

    # Header
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 9.5)
    c.drawString(box_x + 14, box_y + box_h - 18, "TEAM DETAILS")

    # Left Column
    dy = box_y + box_h - 38
    details_left = [
        ("TEAM NAME", ":", team_name[:28]),
        ("TEAM SIZE", ":", size_label),
        ("LEAD MEMBER", ":", leader_name[:28]),
        ("COLLEGE", ":", college[:36])
    ]
    for lbl, col_sign, val in details_left:
        c.setFillColor(HexColor('#7dd3fc'))
        c.setFont('Helvetica', 8)
        c.drawString(box_x + 14, dy, lbl)
        c.setFillColor(HexColor('#00A3FF'))
        c.drawString(box_x + 95, dy, col_sign)
        c.setFillColor(HexColor('#ffffff'))
        c.setFont('Helvetica-Bold', 8)
        c.drawString(box_x + 105, dy, val)
        dy -= 19

    # Vertical Column Divider
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(0.8)
    c.line(box_x + 400, box_y + 12, box_x + 400, box_y + box_h - 12)

    # Right Column: Team Members Roster
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 9)
    c.drawString(box_x + 418, box_y + box_h - 18, "TEAM MEMBERS")

    m_list = members if members else [{'name': leader_name, 'role': 'leader'}]
    dy_m = box_y + box_h - 38
    for idx, m in enumerate(m_list[:3]):
        m_name = m.get('name', f"Member {idx+1}")
        is_lead = (idx == 0 or m.get('role') == 'leader')
        c.setFillColor(HexColor('#00E5FF'))
        c.setFont('Helvetica-Bold', 8)
        c.drawString(box_x + 418, dy_m, f"{idx+1}.")
        c.setFillColor(HexColor('#ffffff'))
        c.setFont('Helvetica', 8)
        c.drawString(box_x + 434, dy_m, m_name[:24])
        if is_lead:
            c.setFillColor(HexColor('#38BDF8'))
            c.setFont('Helvetica-Bold', 7.5)
            c.drawString(box_x + 640, dy_m, "(Lead)")
        dy_m -= 19

    # --- 7. Signatures & Center Slogan Box ---
    sig_y = height - 475

    # Faculty Coordinator
    c.setFillColor(HexColor('#E0F2FF'))
    c.setFont('Times-Italic', 16)
    c.drawString(44, sig_y + 20, "Deepak Sharma")
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1)
    c.line(44, sig_y + 14, 180, sig_y + 14)

    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 8)
    c.drawString(44, sig_y + 3, "FACULTY COORDINATOR")
    c.setFillColor(HexColor('#7dd3fc'))
    c.setFont('Helvetica', 6.5)
    c.drawString(44, sig_y - 7, "DEPT. OF DATA SCIENCE & IT")
    c.drawString(44, sig_y - 16, "TOLANI COLLEGE")

    # Center Slogan Box
    slog_w = 260
    slog_h = 36
    slog_x = 270
    slog_box_y = sig_y - 16
    c.setFillColor(HexColor('#061433'))
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1)
    c.roundRect(slog_x, slog_box_y, slog_w, slog_h, 6, fill=1, stroke=1)

    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(slog_x + slog_w / 2, slog_box_y + 20, "// THINK BEYOND. BUILD FEARLESSLY. //")
    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica', 7)
    c.drawCentredString(slog_x + slog_w / 2, slog_box_y + 8, "SUPERNOVA 2026")

    # Event Convenor / Chairperson
    c.setFillColor(HexColor('#E0F2FF'))
    c.setFont('Times-Italic', 16)
    c.drawRightString(760, sig_y + 20, "Karan Manikandan")
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1)
    c.line(624, sig_y + 14, 760, sig_y + 14)

    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 8)
    c.drawRightString(760, sig_y + 3, "CHAIRPERSON")
    c.setFillColor(HexColor('#7dd3fc'))
    c.setFont('Helvetica', 6.5)
    c.drawRightString(760, sig_y - 7, "SUPERNOVA 2026")
    c.drawRightString(760, sig_y - 16, "TOLANI COLLEGE")

    # Micro Legal Footer
    c.setFillColor(HexColor('#38BDF8'))
    c.setFont('Helvetica', 6)
    c.drawString(44, 20, "THIS PASS IS NON-TRANSFERABLE. VALID ONLY FOR SUPERNOVA QUANTUM HACK 2026.")
    c.drawRightString(760, 20, "ORGANISED BY DEPARTMENT OF DATA SCIENCE & IT | TOLANI COLLEGE")

    # --- 8. RIGHT VERIFICATION STUB (x=780 to 988) ---
    stub_cx = 884

    # Header
    c.setFillColor(HexColor('#00E5FF'))
    c.setFont('Helvetica-Bold', 9.5)
    c.drawCentredString(stub_cx, height - 38, "REGISTRATION PASS")
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(0.8)
    c.line(800, height - 46, 968, height - 46)

    # Scannable High-Contrast QR Code
    try:
        qr = qrcode.QRCode(box_size=4, border=1)
        qr_url = f"{base_url}/?ref={team_id}"
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='black', back_color='white')
        
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format='PNG')
        qr_buf.seek(0)
        
        # White container
        c.setFillColor(HexColor('#ffffff'))
        c.roundRect(stub_cx - 58, height - 180, 116, 116, 10, fill=1, stroke=0)
        c.drawImage(ImageReader(qr_buf), stub_cx - 54, height - 176, 108, 108)
    except Exception:
        pass

    c.setFillColor(HexColor('#38BDF8'))
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(stub_cx, height - 194, "SCAN FOR VERIFICATION")

    # Registration ID and Status Card
    rc_w = 176
    rc_h = 86
    rc_x = stub_cx - (rc_w / 2)
    rc_y = height - 296

    c.setFillColor(HexColor('#061433'))
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(1)
    c.roundRect(rc_x, rc_y, rc_w, rc_h, 8, fill=1, stroke=1)

    c.setFillColor(HexColor('#7dd3fc'))
    c.setFont('Helvetica-Bold', 7.5)
    c.drawCentredString(stub_cx, rc_y + rc_h - 16, "REGISTRATION ID")

    c.setFillColor(HexColor('#ffffff'))
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(stub_cx, rc_y + rc_h - 34, team_id)

    c.setFillColor(HexColor('#7dd3fc'))
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(stub_cx, rc_y + rc_h - 50, "STATUS")

    # Emerald Green Verified Capsule
    c.setFillColor(HexColor('#022c16'))
    c.setStrokeColor(HexColor('#22c55e'))
    c.setLineWidth(1)
    c.roundRect(stub_cx - 48, rc_y + 8, 96, 18, 9, fill=1, stroke=1)

    c.setFillColor(HexColor('#4ade80'))
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(stub_cx, rc_y + 14, "✓ VERIFIED")

    # 3 Event Highlight Chips at Bottom
    c.setStrokeColor(HexColor('#00A3FF'))
    c.setLineWidth(0.8)
    c.line(rc_x, rc_y - 12, rc_x + rc_w, rc_y - 12)

    chips = [
        ("₹6,000", "TOTAL PRIZE POOL", "T"),
        ("TOP 10", "INTERNSHIP SLOTS", "I"),
        ("1-DAY INTENSIVE", "07:30 AM - 04:30 PM IST", "M")
    ]
    cy = rc_y - 42
    for val_c, sub_c, ic_char in chips:
        # Icon box
        c.setFillColor(HexColor('#0a2048'))
        c.setStrokeColor(HexColor('#00E5FF'))
        c.setLineWidth(0.8)
        c.roundRect(rc_x + 4, cy, 22, 22, 4, fill=1, stroke=1)

        c.setFillColor(HexColor('#00E5FF'))
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(rc_x + 15, cy + 6, ic_char)

        c.setFillColor(HexColor('#ffffff'))
        c.setFont('Helvetica-Bold', 8.5)
        c.drawString(rc_x + 32, cy + 12, val_c)

        c.setFillColor(HexColor('#38BDF8'))
        c.setFont('Helvetica', 6.5)
        c.drawString(rc_x + 32, cy + 3, sub_c)
        cy -= 30

    c.save()
    return buf.getvalue()
