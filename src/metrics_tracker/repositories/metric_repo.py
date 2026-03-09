import json
import sqlite3

import pandas as pd

from metrics_tracker.models import LogEntry, MetricDefinition


def create_metric(
    conn: sqlite3.Connection, metric: MetricDefinition
) -> MetricDefinition:
    cursor = conn.execute(
        "INSERT INTO metrics (user_id, name, value_type, unit, definition_json, color) VALUES (?, ?, ?, ?, ?, ?)",
        (
            metric.user_id,
            metric.name,
            metric.value_type,
            metric.unit,
            metric.to_definition_json(),
            metric.color,
        ),
    )
    conn.commit()
    assert cursor.lastrowid is not None
    metric.id = cursor.lastrowid
    return metric


def get_metrics_for_user(
    conn: sqlite3.Connection, user_id: int
) -> list[MetricDefinition]:
    rows = conn.execute(
        "SELECT * FROM metrics WHERE user_id = ?", (user_id,)
    ).fetchall()
    return [MetricDefinition.from_row(dict(r)) for r in rows]


def get_metric_by_id(
    conn: sqlite3.Connection, metric_id: int
) -> MetricDefinition | None:
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
    assert cursor.lastrowid is not None
    entry.id = cursor.lastrowid
    return entry


# def get_logs_for_metric(conn: sqlite3.Connection, metric_id: int) -> list[LogEntry]:
#     rows = conn.execute(
#         "SELECT * FROM logs WHERE metric_id = ? ORDER BY recorded_at", (metric_id,)
#     ).fetchall()
#     return [LogEntry.from_row(dict(r)) for r in rows]


# def get_latest_log(conn: sqlite3.Connection, metric_id: int) -> LogEntry | None:
#     row = conn.execute(
#         "SELECT * FROM logs WHERE metric_id = ? ORDER BY recorded_at DESC LIMIT 1",
#         (metric_id,),
#     ).fetchone()
#     if not row:
#         return None
#     return LogEntry.from_row(dict(row))


# def get_logs_since(
#     conn: sqlite3.Connection, metric_id: int, since_ts: int
# ) -> list[LogEntry]:
#     rows = conn.execute(
#         "SELECT * FROM logs WHERE metric_id = ? AND recorded_at >= ? ORDER BY recorded_at",
#         (metric_id, since_ts),
#     ).fetchall()
#     return [LogEntry.from_row(dict(r)) for r in rows]


def get_logs_for_metric(
    conn: sqlite3.Connection, metric_id: int, tz: str
) -> pd.DataFrame:
    query = "SELECT id, name, definition_json FROM metrics WHERE id = ?"
    metricrow = conn.execute(
        query,
        (metric_id,),
    ).fetchone()
    defn = json.loads(metricrow["definition_json"])
    metric_id = metricrow["id"]

    if defn["value_type"] == "numeric":
        query = "SELECT id, metric_id, recorded_at, value, properties_json FROM logs WHERE metric_id = :metric_id ORDER BY recorded_at"
    elif defn["value_type"] == "categorical":
        query = "SELECT id, metric_id, recorded_at, label as value, properties_json FROM logs WHERE metric_id = :metric_id ORDER BY recorded_at"
    elif defn["value_type"] == "none":
        query = "SELECT id, metric_id, recorded_at, properties_json FROM logs WHERE metric_id = :metric_id ORDER BY recorded_at"
    else:
        raise RuntimeError(f"Unknown value type {defn['value_type']}!")

    logrows = conn.execute(query, {"metric_id": metric_id}).fetchall()

    logids = [logrow["id"] for logrow in logrows]
    logs = pd.DataFrame(
        data={
            "recorded_at": pd.Series(
                [logrow["recorded_at"] for logrow in logrows],
                dtype=f"datetime64[s, {tz}]",
                index=logids,
            ),
        }
    )

    if defn["value_type"] == "numeric":
        logs["value"] = pd.Series(
            [logrow["value"] for logrow in logrows], dtype="float64", index=logs.index
        )
    elif defn["value_type"] == "categorical":
        logs["value"] = pd.Series(
            [logrow["value"] for logrow in logrows],
            dtype=pd.CategoricalDtype(categories=defn["categories"]),
            index=logs.index,
        )

    for prop in defn.get("properties", []):
        propname = prop["name"]
        propvals = [
            json.loads(logrow["properties_json"])[propname] for logrow in logrows
        ]
        if prop["value_type"] == "numeric":
            logs[propname] = pd.Series(propvals, dtype="float64", index=logs.index)
        elif prop["value_type"] == "categorical":
            propcats = prop["categories"]
            logs[propname] = pd.Series(
                propvals,
                dtype=pd.CategoricalDtype(categories=propcats),
                index=logs.index,
            )
        elif prop["value_type"] == "boolean":
            logs[propname] = pd.Series(propvals, dtype="boolean", index=logs.index)

    return logs
