import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ["DB_PATH"])

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firebase_uid TEXT UNIQUE NOT NULL,
    display_name TEXT,
    email TEXT,
    photo_url TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value_type TEXT NOT NULL CHECK (value_type IN ('numeric', 'categorical', 'none')),
    unit TEXT,
    definition_json TEXT NOT NULL,
    color TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER NOT NULL,
    recorded_at INTEGER NOT NULL,
    value REAL,
    label TEXT,
    properties_json TEXT,
    FOREIGN KEY (metric_id) REFERENCES metrics(id)
);

CREATE INDEX IF NOT EXISTS idx_logs_metric_id ON logs(metric_id);
CREATE INDEX IF NOT EXISTS idx_logs_recorded_at ON logs(recorded_at);
"""

if DB_PATH.exists():
    print("DB already exists!")
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.executescript(SCHEMA_SQL)

conn.execute(
    """INSERT INTO users
    (firebase_uid, display_name, email, created_at)
    VALUES (?, ?, ?, ?)""",
    (
        os.environ["DEMO_FIREBASE_UID"],
        "Demo User",
        "demo@avilaylabs.com",
        datetime.now().timestamp(),
    ),
)
conn.commit()

conn.close()
