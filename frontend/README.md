# SUPERNOVA 2026 - Frontend Presentation Layer

This directory contains the user-facing web applications, administrative dashboards, and client-side rendering assets for SUPERNOVA Quantum Hack 2026.

## Structure & Files

| File | Purpose | Notes |
|---|---|---|
| `index.html` | Public hackathon landing portal, event countdown, interactive registration modal, live eligibility checks, payment proof uploader, and digital pass viewer. | Self-contained Tailwind CSS & vanilla JavaScript |
| `admin.html` | Administrative command center for review, payment verification, manual status overrides, pass re-issue, and CSV export. | Authenticated via secure bearer tokens |
| `tolani-logo.jpg` | High-resolution college logo displayed in headers and on generated passes. | Static image |
| `horror-ambient.mp3` | Cyberpunk ambient theme audio, configured for default playback on user interaction. | Audio asset |
| `html2canvas.min.js` | Client-side DOM canvas renderer for preview image exports. | Vendored JavaScript |
| `jspdf.umd.min.js` | Client-side PDF generator fallback. | Vendored JavaScript |
| `qrcode.min.js` | Client-side QR code generator for ticket stubs and payment verification. | Vendored JavaScript |

## Routing
All frontend assets are served directly by the backend server:
- `/` or `/index.html` -> Serves `frontend/index.html`
- `/admin` or `/admin.html` -> Serves `frontend/admin.html`
- Static assets (`/tolani-logo.jpg`, `/horror-ambient.mp3`, etc.) -> Serves from `frontend/`
