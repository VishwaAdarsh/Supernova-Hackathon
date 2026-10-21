-- SUPERNOVA 2026 SQLite Database Schema
-- Auto-exported

CREATE TABLE admin_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT NOT NULL, admin_user TEXT NOT NULL, action TEXT NOT NULL, previous_status TEXT, new_status TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE admin_sessions (token TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE email_dispatches (id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT NOT NULL, recipient_email TEXT NOT NULL, subject TEXT NOT NULL, status TEXT NOT NULL, error_message TEXT, sent_at TEXT DEFAULT CURRENT_TIMESTAMP, notification_type TEXT DEFAULT 'FINAL_CONFIRMATION');

CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            college TEXT,
            role TEXT DEFAULT 'member',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE teams (
            id TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            leader_name TEXT,
            track TEXT NOT NULL,
            team_size INTEGER NOT NULL DEFAULT 1,
            devices INTEGER NOT NULL DEFAULT 0,
            transaction_id TEXT UNIQUE,
            proof BLOB,
            proof_type TEXT,
            status TEXT NOT NULL,
            member_names TEXT,
            terms_accepted INTEGER NOT NULL DEFAULT 1,
            internship_accepted INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        , payment_status TEXT DEFAULT 'PENDING', verification_status TEXT DEFAULT 'PENDING_VERIFICATION', ticket_status TEXT DEFAULT 'PENDING', ticket_token TEXT, rejection_reason TEXT, fee_amount INTEGER DEFAULT 300, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, proof_path TEXT, payment_submitted_at TEXT, payment_reviewed_at TEXT, payment_review_notes TEXT);

CREATE INDEX idx_admin_actions_team_id ON admin_actions(team_id);

CREATE INDEX idx_email_dispatches_team_id ON email_dispatches(team_id);

CREATE INDEX idx_members_team_id ON members(team_id);

CREATE UNIQUE INDEX idx_members_unique_email 
        ON members(email) WHERE email IS NOT NULL AND email != ''
        ;

CREATE INDEX idx_teams_track ON teams(track);
