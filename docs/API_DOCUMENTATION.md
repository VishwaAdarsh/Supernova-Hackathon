# SUPERNOVA Quantum Hack 2026 — API Documentation

This document describes all REST API endpoints implemented in `server.py`.

---

## Base URL
```
http://localhost:8000
```

---

## 1. Public Endpoints

### 1.1 Live Slot Capacity
Retrieves real-time slot availability for each track based on live database registrations.

- **URL:** `/api/registrations`
- **Method:** `GET`
- **Auth:** None
- **Response (200 OK):**
```json
{
  "web": {
    "total": 15,
    "claimed": 1,
    "remaining": 14
  },
  "ai": {
    "total": 25,
    "claimed": 0,
    "remaining": 25
  },
  "aiml": {
    "total": 25,
    "claimed": 0,
    "remaining": 25
  }
}
```

---

### 1.2 Team Registration
Submits a new team registration or retrieves an existing registration if already registered.

- **URL:** `/api/registrations`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "track": "web",
  "team_name": "Cyber Mavericks",
  "leader_name": "Adarsh Sharma",
  "email": "leader@example.com",
  "phone": "9876543210",
  "college": "Tolani College of Commerce & Science",
  "team_size": 2,
  "members": [
    {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "9876543211",
      "college": "Tolani College of Commerce & Science"
    }
  ],
  "terms_accepted": true,
  "internship_accepted": true
}
```
- **Response (200 OK):**
```json
{
  "status": "success",
  "id": "SN26-XXXXXXXXXX",
  "ticket_token": "token-string",
  "is_eligible": false,
  "payment_status": "PENDING",
  "verification_status": "PENDING",
  "fee_amount": 300,
  "fee_formatted": "₹300"
}
```
- **Error Response (400 Bad Request):**
```json
{
  "error": "A valid leader email address is required."
}
```

---

### 1.3 Ticket Status Lookup
Looks up a registration record by Reference ID (`SN26-...`) or leader's registered email.

- **URL:** `/api/ticket/:ref`
- **Method:** `GET`
- **Params:** `ref` — Reference ID or email address (URL-encoded)
- **Response (200 OK):**
```json
{
  "id": "SN26-F5122A0DEB",
  "team_name": "Team karanmanikandan",
  "leader_name": "karanmanikandan",
  "email": "karan@example.com",
  "track": "web",
  "track_label": "Web Debugging",
  "team_size": 2,
  "college": "Tolani College",
  "members": ["karanmanikandan", "vishwa kumar"],
  "payment_status": "PAID",
  "verification_status": "VERIFIED",
  "ticket_status": "CONFIRMED",
  "is_eligible": true,
  "fee_amount": 300,
  "fee_formatted": "₹300",
  "has_proof": true,
  "proof_url": "/api/ticket/SN26-F5122A0DEB/proof"
}
```

---

### 1.4 Vector PDF Pass Download
Generates and downloads the official landscape vector PDF pass (1000x562 pt) for an eligible team.

- **URL:** `/api/ticket/:ref/pdf`
- **Method:** `GET`
- **Response (200 OK):** Binary PDF data (`Content-Type: application/pdf`).

---

### 1.5 Payment Proof Submission
Uploads UPI transaction ID and receipt screenshot for organizer verification.

- **URL:** `/api/registrations/:id/payment-proof`
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "transaction_id": "UPI123456789012",
  "proof_base64": "data:image/jpeg;base64,...",
  "proof_filename": "screenshot.jpg"
}
```
- **Response (200 OK):**
```json
{
  "status": "success",
  "message": "Payment proof submitted for review."
}
```

---

### 1.6 Organizer Payment QR Code
Fetches current organizer UPI QR code configuration.

- **URL:** `/api/organizer-qr`
- **Method:** `GET`
- **Response (200 OK):**
```json
{
  "has_qr": true,
  "upi_id": "organizer@okaxis",
  "amount": 300,
  "image_url": "/api/organizer-qr/image"
}
```

---

## 2. Administrative Endpoints (Protected)

Admin endpoints require authentication via Bearer token:
`Authorization: Bearer <token>` or session cookie.

### 2.1 Admin Login
- **URL:** `/api/admin/login`
- **Method:** `POST`
- **Body:** `{"username": "admin", "password": "supernova2026#admin"}`
- **Response (200 OK):** `{"status": "success", "token": "session-token-string"}`

### 2.2 Admin Dashboard Telemetry
- **URL:** `/api/admin/dashboard`
- **Method:** `GET`
- **Response (200 OK):** Aggregate counts, revenue, track breakdown, and recent actions.

### 2.3 Registration Management
- `GET /api/admin/registrations` — Lists teams with optional `?track=web&status=VERIFIED&search=query`
- `GET /api/admin/registrations/:id` — Full details of a single registration
- `POST /api/admin/registrations/:id/verify-payment` — Confirms payment receipt (`PAID`)
- `POST /api/admin/registrations/:id/reject-payment` — Flags payment issue (`REJECTED`)
- `POST /api/admin/registrations/:id/approve-registration` — Approves entry (`VERIFIED`)
- `POST /api/admin/registrations/:id/reject-registration` — Disqualifies or rejects entry (`REJECTED`)

### 2.4 CSV Export
- **URL:** `/api/admin/export/csv`
- **Method:** `GET`
- **Params:** Optional `?track=all&status=all`
- **Response (200 OK):** `text/csv` stream with complete team and member roster data.
