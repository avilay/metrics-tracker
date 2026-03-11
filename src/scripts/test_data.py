import json
import os
import random
import sqlite3 as sql
from datetime import datetime, timedelta

# from metrics_tracker.utils import COLORS
# TODO: Figure out how to import metrics_tracker.utils.COLORS
COLORS = [
    "#ef5350",  # red-5
    "#ec407a",  # pink-5
    "#ab47bc",  # purple-5
    "#5c6bc0",  # indigo-5
    "#42a5f5",  # blue-5
    "#29b6f6",  # light-blue-5
    "#26c6da",  # cyan-5
    "#26a69a",  # teal-5
    "#66bb6a",  # green-5
    "#9ccc65"  # light-green-5,
    "#d4e157",  # lime-5
    "#ffee58",  # yellow-5
    "#ffca28",  # amber-5
    "#ffa726",  # orange-5
    "#ff7043",  # deep-orange-5
]

INSERT_TEST_USER = """INSERT INTO users
(firebase_uid, display_name, email, created_at)
VALUES (?, ?, ?, ?)"""

INSERT_METRIC = """INSERT INTO metrics
(user_id, name, value_type, unit, definition_json, color)
VALUES (?, ?, ?, ?, ?, ?)
"""

INSERT_LOG = """INSERT INTO logs
(metric_id, recorded_at, value, label, properties_json)
VALUES (?, ?, ?, ?, ?)
"""

SELECT_ID = "SELECT id FROM metrics WHERE rowid = ?"


START_DAY = datetime(
    year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
) - timedelta(days=30)


def rand_time(day_offset: int) -> int:
    # hr between 6AM to 10PM
    hours = random.randint(6, 22)
    minutes = random.randint(0, 60)
    seconds = random.randint(0, 60)
    newdate = START_DAY + timedelta(
        days=day_offset, hours=hours, minutes=minutes, seconds=seconds
    )
    if newdate > datetime.now():
        raise RuntimeError(f"KA-BOOM {newdate}")
    return int(newdate.timestamp())


def insert_testuser(conn: sql.Connection) -> int:
    test_fbuid = os.environ["TEST_USER_FBUID"]
    test_email = os.environ["TEST_USER_EMAIL"]
    testuser = conn.execute(
        "SELECT id FROM users WHERE firebase_uid = ?",
        (os.environ["TEST_USER_FBUID"],),
    ).fetchone()
    if not testuser:
        cur = conn.execute(
            INSERT_TEST_USER,
            (
                test_fbuid,
                "Test User",
                test_email,
                (datetime.now() - timedelta(days=60)).timestamp(),
            ),
        )
        testuser = conn.execute(
            "SELECT id FROM users WHERE rowid = ?",
            (cur.lastrowid,),
        ).fetchone()
    return testuser[0]


def insert_mood(conn: sql.Connection, testuser_id: int) -> None:
    mood_defn = {
        "value_type": "categorical",
        "categories": ["Happy", "Sad", "Angry", "Serene"],
    }
    cur = conn.execute(
        INSERT_METRIC,
        (
            testuser_id,
            "Mood",
            "categorical",
            None,
            json.dumps(mood_defn),
            random.choice(COLORS),
        ),
    )
    mood_id = conn.execute(SELECT_ID, (cur.lastrowid,)).fetchone()[0]
    moodcats = mood_defn["categories"]
    for day in range(30):
        # Zero or more log entries for each day
        for _ in range(random.randint(0, 4)):
            conn.execute(
                INSERT_LOG,
                (mood_id, rand_time(day), None, random.choice(moodcats), None),
            )


def insert_quark(conn: sql.Connection, testuser_id: int) -> None:
    defn = {
        "value_type": "categorical",
        "categories": ["Charm", "Strange", "Up", "Down"],
    }
    conn.execute(
        INSERT_METRIC,
        (
            testuser_id,
            "Quark",
            "categorical",
            None,
            json.dumps(defn),
            random.choice(COLORS),
        ),
    )


def insert_meditate(conn: sql.Connection, testuser_id: int) -> None:
    defn = {"value_type": "none"}
    cur = conn.execute(
        INSERT_METRIC,
        (
            testuser_id,
            "Meditate",
            "none",
            None,
            json.dumps(defn),
            random.choice(COLORS),
        ),
    )
    meditate_id = conn.execute(SELECT_ID, (cur.lastrowid,)).fetchone()[0]
    for day in range(30):
        # Meditate once a day on some days
        for _ in range(random.randint(0, 1)):
            conn.execute(INSERT_LOG, (meditate_id, rand_time(day), None, None, None))


def insert_water(conn: sql.Connection, testuser_id: int) -> None:
    defn = {"value_type": "none"}
    conn.execute(
        INSERT_METRIC,
        (testuser_id, "Water", "none", None, json.dumps(defn), random.choice(COLORS)),
    )


def insert_weight(conn: sql.Connection, testuser_id: int) -> None:
    defn = {"value_type": "numeric", "unit": "lbs"}
    cur = conn.execute(
        INSERT_METRIC,
        (
            testuser_id,
            "Weight",
            "numeric",
            "lbs",
            json.dumps(defn),
            random.choice(COLORS),
        ),
    )
    weight_id = conn.execute(SELECT_ID, (cur.lastrowid,)).fetchone()[0]
    for day in range(30):
        # Measure weight once a day on some days
        for _ in range(random.randint(0, 1)):
            conn.execute(
                INSERT_LOG,
                (weight_id, rand_time(day), random.randint(100, 200), None, None),
            )


def insert_exercise(conn: sql.Connection, testuser_id: int) -> None:
    defn = {"value_type": "numeric", "unit": "minutes"}
    conn.execute(
        INSERT_METRIC,
        (
            testuser_id,
            "Exercise",
            "numeric",
            "minutes",
            json.dumps(defn),
            random.choice(COLORS),
        ),
    )


def main():
    conn = sql.connect(os.environ["DB_PATH"])

    testuser_id = insert_testuser(conn)

    insert_mood(conn, testuser_id)
    insert_quark(conn, testuser_id)

    insert_meditate(conn, testuser_id)
    insert_water(conn, testuser_id)

    insert_weight(conn, testuser_id)
    insert_exercise(conn, testuser_id)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
