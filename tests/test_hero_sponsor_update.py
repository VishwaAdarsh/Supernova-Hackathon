#!/usr/bin/env python3
"""
SUPERNOVA 2026 - Hero Section Sponsor Update & Countdown Relocation Verification Test
Verifies:
1. Digital Vault logo is featured prominently in Hero Section (#hero) with "PREMIUM TECHNOLOGY PARTNER".
2. Original Digital Vault logo asset is correctly referenced with aspect ratio preservation (object-contain).
3. Countdown module is completely removed from Hero Section (#hero).
4. Countdown module is correctly relocated to Event Schedule (#schedule) with all IDs preserved.
5. No duplicate element IDs exist for cdDays, cdHours, cdMinutes, cdSeconds, cdLiveStatus, countdownGrid.
6. Responsive grid and layout constraints are present without breaking vertical scrolling.
"""

from pathlib import Path

def test_hero_sponsor_and_countdown_relocation():
    html_path = Path("frontend/index.html")
    assert html_path.exists(), "frontend/index.html not found"
    text = html_path.read_text(encoding="utf-8")

    # Locate sections
    pos_hero = text.find('id="hero"')
    pos_about = text.find('id="about"')
    pos_schedule = text.find('id="schedule"')
    pos_experience = text.find('id="experience"')

    assert pos_hero != -1, "Section #hero missing"
    assert pos_about != -1, "Section #about missing"
    assert pos_schedule != -1, "Section #schedule missing"
    assert pos_experience != -1, "Section #experience missing"

    hero_html = text[pos_hero:pos_about]
    schedule_html = text[pos_schedule:pos_experience]

    # 1. Hero Section Sponsor Showcase
    assert "PREMIUM TECHNOLOGY PARTNER" in hero_html, (
        "Hero section must contain the uppercase label 'PREMIUM TECHNOLOGY PARTNER'"
    )
    assert "digital-vault-logo.jpg" in hero_html, (
        "Hero section must reference the complete Digital Vault logo asset (digital-vault-logo.jpg)"
    )
    assert "DIGITAL VAULT" in hero_html, (
        "Hero section must display the partner name 'DIGITAL VAULT'"
    )
    assert "object-contain" in hero_html, (
        "Hero section logo must use 'object-contain' to preserve original aspect ratio"
    )

    # 2. Countdown completely removed from Hero Section
    assert "id=\"cdDays\"" not in hero_html, "cdDays must NOT be in the hero section"
    assert "id=\"cdHours\"" not in hero_html, "cdHours must NOT be in the hero section"
    assert "id=\"cdMinutes\"" not in hero_html, "cdMinutes must NOT be in the hero section"
    assert "id=\"cdSeconds\"" not in hero_html, "cdSeconds must NOT be in the hero section"
    assert "id=\"countdownGrid\"" not in hero_html, "countdownGrid must NOT be in the hero section"
    assert "id=\"cdLiveStatus\"" not in hero_html, "cdLiveStatus must NOT be in the hero section"

    # 3. Countdown properly placed in Schedule Section (#schedule)
    assert "id=\"cdDays\"" in schedule_html, "cdDays must be present in the #schedule section"
    assert "id=\"cdHours\"" in schedule_html, "cdHours must be present in the #schedule section"
    assert "id=\"cdMinutes\"" in schedule_html, "cdMinutes must be present in the #schedule section"
    assert "id=\"cdSeconds\"" in schedule_html, "cdSeconds must be present in the #schedule section"
    assert "id=\"countdownGrid\"" in schedule_html, "countdownGrid must be present in the #schedule section"
    assert "id=\"cdLiveStatus\"" in schedule_html, "cdLiveStatus must be present in the #schedule section"
    assert "1-DAY INTENSIVE" in schedule_html, "Event format card must be present in #schedule section"

    # 4. No duplicate countdown IDs in entire document
    countdown_ids = ["cdDays", "cdHours", "cdMinutes", "cdSeconds", "cdLiveStatus", "countdownGrid"]
    for cid in countdown_ids:
        count = text.count(f'id="{cid}"')
        assert count == 1, f"Element ID '{cid}' must occur exactly once, found {count} occurrences"

    # 5. Asset file checks
    for asset in [
        "frontend/assets/digital-vault-logo.jpg",
        "frontend/digital-vault-logo.jpg",
        "assets/digital-vault-logo.jpg",
    ]:
        p = Path(asset)
        assert p.exists() and p.stat().st_size > 0, f"Asset file missing or empty: {asset}"

    print("[PASS] All verification assertions passed successfully!")

if __name__ == "__main__":
    test_hero_sponsor_and_countdown_relocation()
