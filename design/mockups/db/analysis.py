import json
import sqlite3 as sql

import pandas as pd


def load_metrics(user_id: int, metric_name: str, tz: str) -> pd.DataFrame:
    conn = sql.connect("./metrics-tracker.db")
    conn.row_factory = sql.Row

    query = "SELECT id, name, definition_json FROM metrics WHERE user_id = :user_id AND name = :metric_name"
    metricrow = conn.execute(
        query, {"user_id": user_id, "metric_name": metric_name}
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
    metric = pd.DataFrame(
        data={
            "recorded_at": pd.Series(
                # [datetime.fromtimestamp(logrow["recorded_at"]) for logrow in logrows],
                [logrow["recorded_at"] for logrow in logrows],
                dtype=f"datetime64[s, {tz}]",
                index=logids,
            ),
        }
    )

    if defn["value_type"] == "numeric":
        metric["value"] = pd.Series(
            [logrow["value"] for logrow in logrows], dtype="float64", index=metric.index
        )
    elif defn["value_type"] == "categorical":
        metric["value"] = pd.Series(
            [logrow["value"] for logrow in logrows],
            dtype=pd.CategoricalDtype(categories=defn["categories"]),
            index=metric.index,
        )

    for prop in defn.get("properties", []):
        propname = prop["name"]
        propvals = [
            json.loads(logrow["properties_json"])[propname] for logrow in logrows
        ]
        if prop["value_type"] == "numeric":
            metric[propname] = pd.Series(propvals, dtype="float64", index=metric.index)
        elif prop["value_type"] == "categorical":
            propcats = prop["categories"]
            metric[propname] = pd.Series(
                propvals,
                dtype=pd.CategoricalDtype(categories=propcats),
                index=metric.index,
            )
        elif prop["value_type"] == "boolean":
            metric[propname] = pd.Series(propvals, dtype="boolean", index=metric.index)

    conn.close()
    return metric
