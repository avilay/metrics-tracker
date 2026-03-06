CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY,
	user_id INTEGER,
    name TEXT NOT NULL,
    unit TEXT,
    value_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY,
	metric_id INTEGER,
    name TEXT NOT NULL,
    value_type TEXT NOT NULL,
	FOREIGN KEY(metric_id) REFERENCES metrics(id)
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY,
	metric_id INTEGER,
    recorded_at INTEGER NOT NULL,  -- timestamp
    numeric_value REAL,
    label_value TEXT,
	FOREIGN KEY(metric_id) REFERENCES metrics(id)
);

CREATE TABLE IF NOT EXISTS logs_props (
    id INTEGER PRIMARY KEY,
	log_id INTEGER,
	property_id INTEGER,
	numeric_value REAL,
    label_value TEXT,
    FOREIGN KEY(log_id) REFERENCES logs(id),
    FOREIGN KEY(property_id) REFERENCES properties(id)
);