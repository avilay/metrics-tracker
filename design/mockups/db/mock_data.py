"""
Insert mock data into the metrics-tracker SQLite database.

Usage:
    python mock_data.py

Creates metrics-tracker.db in the current directory, applies create.sql,
inserts metric definitions from metrics_defn.py, and populates ~4 weeks
of realistic log entries.
"""

import json
import random
import sqlite3
from pathlib import Path
from typing import cast

from metrics_defn import (
    glucose_defn,
    hike_defn,
    meal_defn,
    meditation_defn,
    mood_defn,
    weight_defn,
)

DB_PATH = Path(__file__).parent / "metrics-tracker.db"
SCHEMA_PATH = Path(__file__).parent / "create.sql"

# 4 weeks of data: Jan 6 2026 to Feb 2 2026 (UTC epoch seconds)
START_TS = 1767686400  # 2026-01-06 00:00:00 PST
DAY = 86400
USER_ID = 1


def create_db() -> sqlite3.Connection:
    # Remove existing db to start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def insert_metric(conn: sqlite3.Connection, defn: dict) -> int:
    """Insert a metric definition and return its id."""
    cur = conn.execute(
        "INSERT INTO metrics (user_id, name, value_type, unit, definition_json) VALUES (?, ?, ?, ?, ?)",
        (
            USER_ID,
            defn["name"],
            defn["value_type"],
            defn.get("unit"),
            json.dumps(defn),
        ),
    )
    return cast(int, cur.lastrowid)


def insert_log(
    conn: sqlite3.Connection,
    metric_id: int,
    recorded_at: int,
    value: float | None = None,
    label: str | None = None,
    properties: dict | None = None,
):
    conn.execute(
        "INSERT INTO logs (metric_id, recorded_at, value, label, properties_json) VALUES (?, ?, ?, ?, ?)",
        (
            metric_id,
            recorded_at,
            value,
            label,
            json.dumps(properties) if properties else None,
        ),
    )


def rand_time(day_offset: int) -> int:
    """Return a random timestamp on a given day (offset from START_TS)."""
    base = START_TS + day_offset * DAY
    return base + random.randint(6 * 3600, 22 * 3600)  # between 6am and 10pm


def populate_meditation(conn: sqlite3.Connection, metric_id: int):
    """~4-5 meditation sessions per week for 4 weeks."""
    for week in range(4):
        days = sorted(random.sample(range(7), random.randint(4, 5)))
        for d in days:
            insert_log(conn, metric_id, rand_time(week * 7 + d), value=1)


def populate_weight(conn: sqlite3.Connection, metric_id: int):
    """Daily morning weight measurement, trending down from ~185."""
    weight = 185.0
    for day in range(28):
        weight += random.uniform(-0.8, 0.5)
        insert_log(conn, metric_id, rand_time(day), value=round(weight, 1))


def populate_mood(conn: sqlite3.Connection, metric_id: int):
    """2-3 mood entries per day."""
    moods = mood_defn["categories"]
    for day in range(28):
        n = random.randint(2, 3)
        for _ in range(n):
            insert_log(
                conn, metric_id, rand_time(day), value=1, label=random.choice(moods)
            )


def populate_meal(conn: sqlite3.Connection, metric_id: int):
    """3 meals per day with properties."""
    sources = ["home-cooked", "take-out", "tiffin"]
    tastes = ["delicious", "edible", "bad"]
    healthies = ["very", "medium", "no"]

    for day in range(28):
        for meal_hour in [8, 13, 19]:  # breakfast, lunch, dinner
            ts = START_TS + day * DAY + meal_hour * 3600 + random.randint(0, 1800)
            props = {
                "source": random.choice(sources),
                "taste": random.choice(tastes),
                "is_filling": random.choice([True, False]),
                "healthy": random.choice(healthies),
            }
            insert_log(conn, metric_id, ts, value=1, properties=props)


def populate_glucose(conn: sqlite3.Connection, metric_id: int):
    """1-3 glucose readings per day with event/delta properties."""
    for day in range(28):
        # Fasting reading most mornings
        if random.random() < 0.85:
            ts = START_TS + day * DAY + random.randint(6 * 3600, 8 * 3600)
            insert_log(
                conn,
                metric_id,
                ts,
                value=round(random.uniform(85, 110), 1),
                properties={"event": "fasting", "delta": None},
            )

        # Post-breakfast reading some days
        if random.random() < 0.6:
            delta = random.choice(["one-hour-after", "two-hours-after"])
            offset = 3600 if delta == "one-hour-after" else 7200
            ts = START_TS + day * DAY + 8 * 3600 + offset + random.randint(0, 1800)
            insert_log(
                conn,
                metric_id,
                ts,
                value=round(random.uniform(120, 180), 1),
                properties={"event": "breakfast", "delta": delta},
            )

        # Post-workout reading occasionally
        if random.random() < 0.3:
            ts = START_TS + day * DAY + random.randint(16 * 3600, 19 * 3600)
            insert_log(
                conn,
                metric_id,
                ts,
                value=round(random.uniform(90, 130), 1),
                properties={
                    "event": "workout",
                    "delta": random.choice(["one-hour-after", "two-hours-after"]),
                },
            )


def populate_hike(conn: sqlite3.Connection, metric_id: int):
    """1-2 hikes per week."""
    landscapes = ["coastal", "lake", "river", "mountain", "ridge", "woods"]
    for week in range(4):
        hike_days = sorted(random.sample(range(7), random.randint(1, 2)))
        for d in hike_days:
            length = round(random.uniform(2.0, 12.0), 1)
            elevation = round(random.uniform(50, 800))
            duration = round(length * random.uniform(15, 25))  # mins per mile
            insert_log(
                conn,
                metric_id,
                rand_time(week * 7 + d),
                value=duration,
                properties={
                    "loop_length": length,
                    "elevation_gain": elevation,
                    "landscape": random.choice(landscapes),
                },
            )


def main():
    random.seed(42)
    conn = create_db()

    med_id = insert_metric(conn, meditation_defn)
    weight_id = insert_metric(conn, weight_defn)
    mood_id = insert_metric(conn, mood_defn)
    meal_id = insert_metric(conn, meal_defn)
    glucose_id = insert_metric(conn, glucose_defn)
    hike_id = insert_metric(conn, hike_defn)

    populate_meditation(conn, med_id)
    populate_weight(conn, weight_id)
    populate_mood(conn, mood_id)
    populate_meal(conn, meal_id)
    populate_glucose(conn, glucose_id)
    populate_hike(conn, hike_id)

    conn.commit()

    # Print summary
    for row in conn.execute(
        "SELECT m.name, COUNT(l.id) FROM metrics m LEFT JOIN logs l ON m.id = l.metric_id GROUP BY m.id"
    ):
        print(f"  {row[0]}: {row[1]} logs")

    conn.close()
    print(f"\nDatabase created at {DB_PATH}")


if __name__ == "__main__":
    main()
