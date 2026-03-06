"""
Generate mock data for the metrics-tracker SQLite database.

Metrics based on examples from product_vision.md:
1. Meditation    - value_type: none
2. Weight        - value_type: numeric (lbs)
3. Mood          - value_type: labeled (Happy, Sad, Angry, Serene)
4. Meal          - value_type: none, properties: Source, Taste, Is_Filling, Healthy
5. Blood-Glucose - value_type: numeric (mg/dL), properties: Event, Delta
6. Hike          - value_type: numeric (minutes), properties: Length, Elevation Gain, Landscape
"""

import sqlite3
import random
from pathlib import Path

DB_PATH = Path(__file__).parent / "metrics-tracker.db"
SCHEMA_PATH = Path(__file__).parent / "create.sql"

USER_ID = 1

# Timestamps: Jan 1 2026 to Mar 1 2026 (roughly 60 days)
TS_START = 1735689600  # Jan 1, 2026 00:00 UTC
TS_END = 1740873600    # Mar 1, 2026 00:00 UTC


def random_ts(start=TS_START, end=TS_END):
    return random.randint(start, end)


def sorted_timestamps(n, start=TS_START, end=TS_END):
    return sorted(random_ts(start, end) for _ in range(n))


def init_db(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS logs_props;
        DROP TABLE IF EXISTS logs;
        DROP TABLE IF EXISTS properties;
        DROP TABLE IF EXISTS metrics;
    """)
    schema = SCHEMA_PATH.read_text()
    conn.executescript(schema)


def insert_metric(conn, name, value_type, unit=None):
    cur = conn.execute(
        "INSERT INTO metrics (user_id, name, unit, value_type) VALUES (?, ?, ?, ?)",
        (USER_ID, name, unit, value_type),
    )
    return cur.lastrowid


def insert_property(conn, metric_id, name, value_type):
    cur = conn.execute(
        "INSERT INTO properties (metric_id, name, value_type) VALUES (?, ?, ?)",
        (metric_id, name, value_type),
    )
    return cur.lastrowid


def insert_log(conn, metric_id, recorded_at, numeric_value=None, label_value=None):
    cur = conn.execute(
        "INSERT INTO logs (metric_id, recorded_at, numeric_value, label_value) VALUES (?, ?, ?, ?)",
        (metric_id, recorded_at, numeric_value, label_value),
    )
    return cur.lastrowid


def insert_log_prop(conn, log_id, property_id, numeric_value=None, label_value=None):
    conn.execute(
        "INSERT INTO logs_props (log_id, property_id, numeric_value, label_value) VALUES (?, ?, ?, ?)",
        (log_id, property_id, numeric_value, label_value),
    )


def gen_meditation(conn):
    """Meditation: no value, no properties. ~30 sessions over 2 months."""
    metric_id = insert_metric(conn, "Meditation", "none")
    for ts in sorted_timestamps(30):
        insert_log(conn, metric_id, ts)
    return metric_id


def gen_weight(conn):
    """Weight: numeric value (lbs), no properties. ~40 readings."""
    metric_id = insert_metric(conn, "Weight", "numeric", unit="lbs")
    weight = 185.0
    for ts in sorted_timestamps(40):
        weight += random.gauss(0, 0.8)
        weight = round(max(160, min(210, weight)), 1)
        insert_log(conn, metric_id, ts, numeric_value=weight)
    return metric_id


def gen_mood(conn):
    """Mood: labeled value (Happy, Sad, Angry, Serene). ~50 entries."""
    labels = ["Happy", "Sad", "Angry", "Serene"]
    weights = [0.4, 0.2, 0.1, 0.3]
    metric_id = insert_metric(conn, "Mood", "labeled")
    for ts in sorted_timestamps(50):
        label = random.choices(labels, weights=weights, k=1)[0]
        insert_log(conn, metric_id, ts, label_value=label)
    return metric_id


def gen_meal(conn):
    """Meal: no value, 4 labeled properties. ~90 entries (1-2 meals/day)."""
    metric_id = insert_metric(conn, "Meal", "none")
    source_id = insert_property(conn, metric_id, "Source", "labeled")
    taste_id = insert_property(conn, metric_id, "Taste", "labeled")
    filling_id = insert_property(conn, metric_id, "Is_Filling", "labeled")
    healthy_id = insert_property(conn, metric_id, "Healthy", "labeled")

    sources = ["Home-Cooked", "Take-Out", "Tiffin"]
    source_weights = [0.5, 0.3, 0.2]
    tastes = ["Delicious", "Edible", "Bad"]
    taste_weights = [0.4, 0.5, 0.1]
    fillings = ["True", "False"]
    filling_weights = [0.7, 0.3]
    healthys = ["Very", "Medium", "No"]
    healthy_weights = [0.3, 0.5, 0.2]

    for ts in sorted_timestamps(90):
        log_id = insert_log(conn, metric_id, ts)
        insert_log_prop(
            conn, log_id, source_id,
            label_value=random.choices(sources, weights=source_weights, k=1)[0],
        )
        insert_log_prop(
            conn, log_id, taste_id,
            label_value=random.choices(tastes, weights=taste_weights, k=1)[0],
        )
        insert_log_prop(
            conn, log_id, filling_id,
            label_value=random.choices(fillings, weights=filling_weights, k=1)[0],
        )
        insert_log_prop(
            conn, log_id, healthy_id,
            label_value=random.choices(healthys, weights=healthy_weights, k=1)[0],
        )
    return metric_id


def gen_blood_glucose(conn):
    """Blood-Glucose: numeric value (mg/dL), 2 labeled properties. ~45 entries."""
    metric_id = insert_metric(conn, "Blood-Glucose", "numeric", unit="mg/dL")
    event_id = insert_property(conn, metric_id, "Event", "labeled")
    delta_id = insert_property(conn, metric_id, "Delta", "labeled")

    events = ["Fasting", "Breakfast", "Workout", "Ad-Hoc"]
    event_weights = [0.3, 0.35, 0.2, 0.15]
    deltas = ["One-Hour-After", "Two-Hours-After"]

    glucose_ranges = {
        "Fasting": (85, 110),
        "Breakfast": (120, 180),
        "Workout": (90, 130),
        "Ad-Hoc": (95, 150),
    }

    for ts in sorted_timestamps(45):
        event = random.choices(events, weights=event_weights, k=1)[0]
        low, high = glucose_ranges[event]
        value = round(random.uniform(low, high), 1)
        log_id = insert_log(conn, metric_id, ts, numeric_value=value)
        insert_log_prop(conn, log_id, event_id, label_value=event)
        # Delta only applies to non-fasting events
        if event != "Fasting":
            delta = random.choice(deltas)
            insert_log_prop(conn, log_id, delta_id, label_value=delta)
    return metric_id


def gen_hike(conn):
    """Hike: numeric value (minutes), 2 numeric + 1 labeled property. ~20 entries."""
    metric_id = insert_metric(conn, "Hike", "numeric", unit="Minutes")
    length_id = insert_property(conn, metric_id, "Length", "numeric")
    elev_id = insert_property(conn, metric_id, "Elevation Gain", "numeric")
    landscape_id = insert_property(conn, metric_id, "Landscape", "labeled")

    landscapes = ["Coastal", "Lake", "River", "Mountain", "Ridge", "Woods"]

    for ts in sorted_timestamps(20):
        length_mi = round(random.uniform(1.5, 14.0), 1)
        elev_ft = round(random.uniform(50, 3000))
        # Duration roughly correlates with length and elevation
        minutes = round(length_mi * 18 + elev_ft * 0.02 + random.gauss(0, 15))
        minutes = max(20, minutes)

        log_id = insert_log(conn, metric_id, ts, numeric_value=minutes)
        insert_log_prop(conn, log_id, length_id, numeric_value=length_mi)
        insert_log_prop(conn, log_id, elev_id, numeric_value=elev_ft)
        insert_log_prop(
            conn, log_id, landscape_id,
            label_value=random.choice(landscapes),
        )
    return metric_id


def main():
    random.seed(42)
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        gen_meditation(conn)
        gen_weight(conn)
        gen_mood(conn)
        gen_meal(conn)
        gen_blood_glucose(conn)
        gen_hike(conn)
        conn.commit()

        # Print summary
        for table in ["metrics", "properties", "logs", "logs_props"]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
