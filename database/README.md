# SUPERNOVA 2026 - Database Architecture

The SUPERNOVA 2026 platform utilizes an embedded SQLite database engine configured for high-concurrency event registration, payment audit tracking, and administrative actions.

## Database Location
- **Active Database:** `database/registrations.db`
- **Schema Blueprint:** `database/schema.sql`

## Tables Overview

| Table | Purpose | Key Indices |
|---|---|---|
| `teams` | Master registration records (Team name, leader, track, size, fee, payment status, verification status, proof path, ticket token). | `idx_teams_track` |
| `members` | Team member roster (Name, email, phone, college, role: leader/member). | `idx_members_team_id`, `idx_members_unique_email` |
| `admin_actions` | Audit log of status transitions and administrative overrides. | `idx_admin_actions_team_id` |
| `email_dispatches` | Audit trail of sent emails, delivery statuses, error notes, and timestamps. | `idx_email_dispatches_team_id` |
| `admin_sessions` | Authenticated admin bearer tokens with expiration timestamps. | Primary Key: `token` |
| `sqlite_sequence` | Internal SQLite autoincrement sequence tracker. | - |

## Verification Command
To verify database integrity and view record count:
```bash
python -c "import sqlite3; conn = sqlite3.connect('database/registrations.db'); cur = conn.cursor(); print('Teams:', cur.execute('SELECT count(*) FROM teams').fetchone()[0]); print('Members:', cur.execute('SELECT count(*) FROM members').fetchone()[0])"
```
