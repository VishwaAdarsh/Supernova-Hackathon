SUPERNOVA — QUANTUM HACK 2026
Tolani College of Commerce & Science — Department of Data Science & IT

======================================================================
1. QUICK START
======================================================================
1. Ensure Python 3.10 or newer is installed.
2. Open a terminal in this project directory.
3. Run the registration server:
      python server.py
   (Optional: specify custom port or host via env vars: PORT=8000 HOST=0.0.0.0 python server.py)
4. Open your browser and navigate to:
      http://localhost:8000

======================================================================
2. ARCHITECTURE OVERVIEW
======================================================================
- Frontend (index.html):
  The premium Obsidian Cyber-Horror redesign exported from Google Stitch, fully
  integrated with live REST endpoints. Includes 3D sculptural parallax skull,
  real-time slot capacity sync, audio engine (horror-ambient.mp3), dynamic
  team roster management (Solo, Duo, Trio), digital ticket generation, print
  credential rendering, FAQ accordions, and interactive Tolani venue mapping.

- Backend (server.py):
  Lightweight, production-grade standard-library Python HTTP server with zero pip
  dependencies. Handles GET /api/registrations and POST /api/registrations.
  Equipped with atomic SQLite transactions (BEGIN IMMEDIATE), race condition
  protection, duplicate-email rejection, strict input sanitization, and safe
  schema migrations.

- Database (registrations.db):
  Created automatically upon startup. Tracks teams and individual members with
  all roster metadata, unique IDs (SN26-XXXXXXXXXX), and registration timestamps.

- Archives / Design System:
  - stitch_supernova_hackathon_3d_redesign/: Original Stitch export assets and DESIGN.md.

======================================================================
3. EVENT & REGISTRATION SPECIFICATIONS
======================================================================
- Date & Location: 1 December 2026 at Tolani College of Commerce, Andheri East, Mumbai.
- Tracks:
  * Arena 01: Web Debugging (Cap: 25 slots max) — Cash prize up to Rs 2,000.
  * Arena 02: AI / ML System (Cap: 35 slots max) — Cash prize up to Rs 5,000 + Top 20 Internship Interviews.
- Team Size: Solo (1 Hacker), Duo (2 Hackers), or Trio (3 Hackers).
- Fee Structure: Flat Rs 200 per team, collected and verified on-site during campus badge check-in.
  No online payment is processed through this terminal.
- Live Slots: The terminal polls /api/registrations every 30 seconds and refreshes immediately
  after each successful registration.
======================================================================
