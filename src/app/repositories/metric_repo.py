import json
import sqlite3

from app.models import LogEntry, MetricDefinition


def create_metric(conn: sqlite3.Connection, metric: MetricDefinition) -> MetricDefinition:
    cursor = conn.execute(
        "INSERT INTO metrics (user_id, name, value_type, unit, definition_json) VALUES (?, ?, ?, ?, ?)",
        (metric.user_id, metric.name, metric.value_type, metric.unit, metric.to_definition_json()),
    )
    conn.commit()
    metric.id = cursor.lastrowid
    return metric


def get_metrics_for_user(conn: sqlite3.Connection, user_id: int) -> list[MetricDefinition]:
    rows = conn.execute(
        "SELECT * FROM metrics WHERE user_id = ? ORDER BY name", (user_id,)
    ).fetchall()
    return [MetricDefinition.from_row(dict(r)) for r in rows]


def get_metric_by_id(conn: sqlite3.Connection, metric_id: int) -> MetricDefinition | None:
    row = conn.execute("SELECT * FROM metrics WHERE id = ?", (metric_id,)).fetchone()
    if not row:
        return None
    return MetricDefinition.from_row(dict(row))


def delete_metric(conn: sqlite3.Connection, metric_id: int) -> None:
    conn.execute("DELETE FROM logs WHERE metric_id = ?", (metric_id,))
    conn.execute("DELETE FROM metrics WHERE id = ?", (metric_id,))
    conn.commit()


def insert_log(conn: sqlite3.Connection, entry: LogEntry) -> LogEntry:
    props_json = json.dumps(entry.properties) if entry.properties else None
    cursor = conn.execute(
        "INSERT INTO logs (metric_id, recorded_at, value, label, properties_json) VALUES (?, ?, ?, ?, ?)",
        (entry.metric_id, entry.recorded_at, entry.value, entry.label, props_json),
    )
    conn.commit()
    entry.id = cursor.lastrowid
    return entry


def get_logs_for_metric(conn: sqlite3.Connection, metric_id: int) -> list[LogEntry]:
    rows = conn.execute(
        "SELECT * FROM logs WHERE metric_id = ? ORDER BY recorded_at", (metric_id,)
    ).fetchall()
    return [LogEntry.from_row(dict(r)) for r in rows]
