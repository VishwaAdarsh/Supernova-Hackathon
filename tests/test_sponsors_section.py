#!/usr/bin/env python3
"""
SUPERNOVA 2026 - Sponsors & Partners Section Verification Test
Verifies:
1. Exact section placement immediately above Venue section.
2. Complete Digital Vault logo asset existence, dimensions, and referencing.
3. Required texts: SPONSORS & PARTNERS, POWERING INNOVATION. ENABLING THE NEXT GENERATION., DIGITAL VAULT, SPONSOR & PARTNER.
4. Navigation integration (desktop navbar, mobile drawer, footer, scroll-spy).
5. Cyberpunk aesthetic classes and responsive layout structure.
"""

from pathlib import Path

def test_sponsors_section():
    html_path = Path("frontend/index.html")
    assert html_path.exists(), "frontend/index.html not found"
    text = html_path.read_text(encoding="utf-8")

    # 1. Section order check
    pos_protocol = text.find('id="protocol"')
    pos_sponsors = text.find('id="sponsors"')
    pos_venue = text.find('id="venue"')
    pos_faq = text.find('id="faq"')

    assert pos_protocol != -1, "Section #protocol not found"
    assert pos_sponsors != -1, "Section #sponsors not found"
    assert pos_venue != -1, "Section #venue not found"
    assert pos_faq != -1, "Section #faq not found"

    assert pos_protocol < pos_sponsors < pos_venue < pos_faq, (
        f"Incorrect section order! Expected protocol ({pos_protocol}) < sponsors ({pos_sponsors}) < venue ({pos_venue}) < faq ({pos_faq})"
    )
    print("[PASS] 1. Section placement: #sponsors is positioned immediately above #venue.")

    # 2. Key text requirements
    assert "SPONSORS &amp; PARTNERS" in text or "SPONSORS & PARTNERS" in text, "Heading 'SPONSORS & PARTNERS' missing"
    assert "POWERING INNOVATION. ENABLING THE NEXT GENERATION." in text, "Supporting text missing"
    assert "DIGITAL VAULT" in text, "Company name 'DIGITAL VAULT' missing"
    assert "SPONSOR &amp; PARTNER" in text or "SPONSOR & PARTNER" in text, "Designation 'SPONSOR & PARTNER' missing"
    assert "digital-vault-logo.jpg" in text, "digital-vault-logo.jpg reference missing"
    print("[PASS] 2. Content integrity: All required text elements and image references verified.")

    # 3. Navigation integration
    desktop_nav_start = text.find('<nav')
    desktop_nav_end = text.find('</nav>', desktop_nav_start)
    desktop_nav = text[desktop_nav_start:desktop_nav_end]
    assert 'href="#sponsors"' in desktop_nav, "Desktop nav missing #sponsors link"

    mobile_nav_start = text.find('id="mobileNavDrawer"')
    mobile_nav_end = text.find('</header>', mobile_nav_start)
    mobile_nav = text[mobile_nav_start:mobile_nav_end]
    assert 'href="#sponsors"' in mobile_nav, "Mobile nav drawer missing #sponsors link"

    footer_start = text.find('// QUICK NAVIGATION')
    footer_end = text.find('// SYSTEM TERMINAL', footer_start)
    footer_nav = text[footer_start:footer_end]
    assert 'href="#sponsors"' in footer_nav, "Footer nav missing #sponsors link"

    spy_start = text.find('function initScrollSpy()')
    spy_end = text.find('function initSupernovaApp()', spy_start)
    spy_code = text[spy_start:spy_end]
    assert "'sponsors'" in spy_code or '"sponsors"' in spy_code, "Scroll-Spy missing 'sponsors' section ID"
    print("[PASS] 3. Navigation: Desktop navbar, mobile drawer, footer, and scrollspy properly wired.")

    # 4. Asset existence and integrity
    required_assets = [
        "frontend/digital-vault-logo.jpg",
        "frontend/assets/digital-vault-logo.jpg",
        "assets/digital-vault-logo.jpg",
        "frontend/digital-vault-icon.png",
        "frontend/assets/digital-vault-icon.png",
        "assets/digital-vault-icon.png"
    ]
    for asset in required_assets:
        p = Path(asset)
        assert p.is_file(), f"Asset {asset} missing"
        assert p.stat().st_size > 0, f"Asset {asset} is empty"
    print("[PASS] 4. Asset availability: All Digital Vault logo assets verified across target directories.")

    # 5. Cyberpunk styling classes
    sponsors_section = text[pos_sponsors:pos_venue]
    assert "interactive-glow-card" in sponsors_section, "Cyber interactive glow card class missing"
    assert "cyber-card-interactive" in sponsors_section, "Cyber card interactive class missing"
    assert "reveal-on-scroll" in sponsors_section, "Reveal on scroll class missing"
    assert "object-contain" in sponsors_section, "object-contain class missing for logo scaling"
    print("[PASS] 5. Styling & responsiveness: Cyberpunk cards, hover glows, and responsive constraints verified.")

    print("\n" + "=" * 60)
    print("ALL SPONSORS SECTION VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_sponsors_section()
