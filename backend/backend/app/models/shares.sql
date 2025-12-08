CREATE TABLE IF NOT EXISTS shares (
    id TEXT PRIMARY KEY,
    artifact_url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    created_at TEXT,
    user_id TEXT
);
