# SUPERNOVA 2026 - Backend Services

This directory contains the core backend services for the SUPERNOVA Quantum Hack 2026 platform.

## Modules

| File | Responsibilities | Key Functions / Classes |
|---|---|---|
| `server.py` | Multi-threaded HTTP server (`ThreadingHTTPServer`), REST API routing, participant registration, status transitions, admin session auth, organizer QR configuration, proof upload validation, and CSV reporting. | `Server`, `run_server()`, `handle_registration()`, `handle_admin_auth()` |
| `email_service.py` | SMTP mailer service with retry mechanics, HTML & plain-text templates with quantum cyberpunk styling, and audit logging into SQLite and file logs. | `send_email_notification()`, `get_smtp_config()`, `render_email_template()` |
| `pdf_generator.py` | ReportLab-based vector PDF pass generation (1000x562 widescreen, cyan neon aesthetic, dual signatures, dynamic QR verification stub). | `generate_pass_pdf()`, `is_pdf_supported()` |

## Running the Backend
From the repository root:
```bash
python server.py
```
Or directly from the backend module:
```bash
python backend/server.py
```

Default port is `8000`. Set `PORT` environment variable to override.
