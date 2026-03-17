-- Initial schema for ecs-sandbox

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'active',
    container_id    TEXT,
    container_ip    TEXT,
    created_at      INTEGER NOT NULL,
    last_active_at  INTEGER NOT NULL,
    expires_at      INTEGER,
    workspace_path  TEXT,
    metadata        TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    seq             INTEGER NOT NULL,
    kind            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    payload         TEXT NOT NULL,
    result          TEXT,
    submitted_at    INTEGER NOT NULL,
    completed_at    INTEGER,
    UNIQUE(session_id, seq)
);

CREATE INDEX IF NOT EXISTS idx_events_session_seq ON events(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_sessions_status_active ON sessions(status, last_active_at);
