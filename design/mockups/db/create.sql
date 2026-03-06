CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value_type TEXT NOT NULL CHECK (value_type IN ('numeric', 'categorical', 'none')),
    unit TEXT,
    definition_json TEXT NOT NULL
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
