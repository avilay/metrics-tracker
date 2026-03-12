import os
import sqlite3
from pathlib import Path

from nicegui import app, ui

DB_PATH = Path(os.environ["DB_PATH"])

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


async def detect_timezone() -> str:
    """Detect the browser's timezone via JavaScript and cache it in app.storage.user.

    Returns the IANA timezone string (e.g. "US/Pacific", "America/New_York").
    The result is refreshed on every call (i.e. every new page load / session).
    """
    tz = await ui.run_javascript("Intl.DateTimeFormat().resolvedOptions().timeZone")
    app.storage.user["tz"] = tz
    return tz


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
