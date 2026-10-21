# SUPERNOVA // QUANTUM HACK 2026

> **Tolani College of Commerce & Science — Department of Data Science & IT**  
> *1 December 2026 • Andheri East, Mumbai*  
> `"Think Beyond. Build Fearlessly."`

---

## Architecture & Directory Structure

The project has been professionally organized into a modular, clean, and maintainable architecture separating frontend presentation, backend logic, and database management:

```
Hackathon website/
│
├── frontend/                     # UI, pages, styles, client JS, audio, and web assets
│   ├── index.html                # Public registration portal & digital pass viewer
│   ├── admin.html                # Organizer review & verification command center
│   ├── tolani-logo.jpg           # Official college branding logo
│   ├── horror-ambient.mp3        # Default theme audio asset
│   ├── html2canvas.min.js        # DOM to canvas capture library
│   ├── jspdf.umd.min.js          # Client-side PDF fallback library
│   ├── qrcode.min.js             # Client-side QR generation engine
│   └── README.md                 # Frontend architecture & routing guide
│
├── backend/                      # Python backend server and microservices
│   ├── server.py                 # Core HTTP server, REST endpoints, admin handlers
│   ├── email_service.py          # SMTP dispatcher, templates, and delivery engine
│   ├── pdf_generator.py          # ReportLab vector pass generator (1000x562)
│   ├── __init__.py               # Python package initialization
│   └── README.md                 # Backend API & service documentation
│
├── database/                     # Active database, SQL blueprints, and documentation
│   ├── registrations.db          # Production SQLite database (ACID compliant)
│   ├── schema.sql                # Complete schema export for all 6 tables & indices
│   └── README.md                 # Database table relations & verification guide
│
├── assets/                       # Static brand artwork & icons
│   ├── nova-avatar.png           # Cyber astronaut mascot graphic
│   ├── organizer-qr.jpg          # UPI payment QR code
│   ├── instagram-icon.png        # Social channel icon
│   └── whatsapp-icon.png         # Social channel icon
│
├── uploads/                      # Dynamic participant uploads
│   ├── proofs/                   # Participant payment screenshots & receipts
│   └── qr/                       # Generated ticket verification QR images
│
├── docs/                         # Comprehensive engineering documentation
│   ├── ARCHITECTURE.md           # System architecture & request lifecycle
│   ├── API_DOCUMENTATION.md      # Full REST API specification
│   └── AUDIT_REPORT.md           # Architectural audit & risk register
│
├── tests/                        # Automated regression and verification suites
│   ├── test_structure_verification.py   # Multi-tier route & security verification
│   ├── test_smtp_and_pass_pdf.py        # Email transmission & pass generator tests
│   └── test_consolidation_and_live_data.py # Admin lifecycle and database tests
│
├── tools/                        # Maintenance utilities & historical scripts
│   ├── migrate_theme.py
│   ├── update_colors.py
│   ├── update_colors_all.py
│   ├── update_ticket_colors.py
│   └── check_colors.py
│
├── backups/                      # Legacy backup archives (.bak snapshots)
│
├── server.py                     # Root entrypoint (delegates to backend/server.py)
├── email_service.py              # Root wrapper for backward compatibility
├── pdf_generator.py              # Root wrapper for backward compatibility
├── requirements.txt              # Production Python package requirements
├── .env                          # Local environment secrets & port configuration
├── .env.example                  # Environment configuration template
└── README.md                     # Project documentation & reference
```

---

## Tech Stack

- **Frontend:** HTML5, Tailwind CSS, Google Fonts (Syne, Caveat, Plus Jakarta Sans, Space Mono), Canvas 2D matrix skull animation, Web Audio API, `html2canvas`, `jspdf`, `qrcode.js`.
- **Backend:** Python 3.10+ standard library (`http.server`, `urllib`, `sqlite3`, `smtplib`, `hmac`). Zero framework overhead.
- **Credential Engine:** ReportLab vector PDF canvas & dynamic QR code generation.
- **Database:** SQLite 3 (`database/registrations.db`) with `BEGIN IMMEDIATE` ACID transaction isolation.

---

## Quick Start

### 1. Requirements
- Python 3.10 or higher.
- Install credential dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` to configure custom SMTP delivery credentials or admin credentials:
```bash
cp .env.example .env
```

### 3. Launch the Server
You can launch the server using either the root entrypoint or directly from the backend module:
```bash
python server.py
# Or:
python backend/server.py
```
*(Optionally specify custom port: `PORT=8080 python server.py`)*

### 4. Access the Interfaces
- **Main Hackathon Portal:** [http://localhost:8000/](http://localhost:8000/)
- **Admin Command Terminal:** [http://localhost:8000/admin](http://localhost:8000/admin)
  - Default Username: `admin`
  - Default Password: `supernova2026#admin` *(configured via `ADMIN_PASSWORD` env var)*

---

## Key Features

1. **Atomic Track Quotas:** Live capacity enforcement for Web Debugging (15 slots) and AI/ML (25 slots) with race condition immunity.
2. **Duplicate Protection:** Duplicate emails are detected automatically; returning teams receive their existing status rather than duplicate entries.
3. **Payment Proof Verification:** Registrants submit UPI transaction IDs and screenshot receipts for organizer inspection.
4. **Official Ticket Pass:** High-fidelity 1000×562 landscape pass featuring cybernetic chamfered borders, scannable QR verification, team roster, signatures, and instant export to vector PDF or high-res PNG.
5. **Admin Portal:** Live telemetry, registration search/filtering, modal proof inspection, approval workflows, and one-click CSV roster export.

---

## Testing & Verification

Run the structure & security verification suite:
```bash
python tests/test_structure_verification.py
```

Run pass & admin verification:
```bash
python tests/test_consolidation_and_live_data.py
```

Run SMTP & PDF verification:
```bash
python tests/test_smtp_and_pass_pdf.py
```

---

## Documentation

- [Architecture & System Design](docs/ARCHITECTURE.md)
- [REST API Documentation](docs/API_DOCUMENTATION.md)
- [Comprehensive Audit Report](docs/AUDIT_REPORT.md)
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)
- [Database Documentation](database/README.md)
