# flake8: noqa: E731

from contextlib import closing
from typing import cast

import humanize
import pandas as pd
from nicegui import app, ui

from metrics_tracker.models import MetricDefinition
from metrics_tracker.repositories.metric_repo import (
    get_logs_for_metric,
    get_metric_by_id,
)
from metrics_tracker.utils import get_connection

TIME_RANGE_LABEL = {"D": "Hour", "W": "Day", "M": "Week", "6M": "Month", "Y": "Month"}
TIME_RANGES = ["D", "W", "M", "6M", "Y"]


def _aggregate_none_metric(
    logs: pd.DataFrame, time_range: str, tz: str
) -> tuple[list[str], list[int]]:
    """Aggregate a none-value-type metric into (labels, counts) for chart and table."""
    now = pd.Timestamp.now(tz=tz)

    if time_range == "D":
        window_start = now.normalize()
        freq = "h"
        full_range = pd.date_range(window_start, now, freq=freq)
        fmt = humanize.naturaltime
    elif time_range == "W":
        # Monday of current week
        window_start = now.normalize() - pd.DateOffset(days=now.dayofweek)
        freq = "D"
        full_range = pd.date_range(window_start, now, freq=freq)
        fmt = humanize.naturalday
    elif time_range == "M":
        window_start = now.normalize().replace(day=1)
        freq = "W"
        full_range = pd.date_range(window_start, now, freq=freq)
        fmt = humanize.naturaldate
    elif time_range == "6M":
        # Go back 6 months (current month is -1)
        month = now.month - 6  # e.g., March(3) - 6 = -3
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        window_start = pd.Timestamp(year=year, month=month, day=1, tz=tz)
        freq = "MS"
        full_range = pd.date_range(window_start, now, freq=freq)
        fmt = lambda ts: ts.strftime("%b")
    elif time_range == "Y":
        window_start = pd.Timestamp(year=now.year, month=1, day=1, tz=tz)
        freq = "MS"
        full_range = pd.date_range(window_start, now, freq=freq)
        fmt = lambda ts: ts.strftime("%b")
    else:
        raise ValueError(f"Unknown time range: {time_range}")

    if logs.empty:
        labels = [fmt(ts) for ts in full_range]
        counts = [0] * len(labels)
        return labels, counts

    filtered = logs[logs["recorded_at"] >= window_start]

    if filtered.empty:
        labels = [fmt(ts) for ts in full_range]
        counts = [0] * len(labels)
        return labels, counts

    resampled = (
        filtered.resample(freq, on="recorded_at")
        .size()
        .reindex(full_range, fill_value=0)
    )

    labels = [fmt(ts) for ts in resampled.index]
    counts: list[int] = cast(list[int], resampled.values.tolist())
    return labels, counts


def _build_chart_options(
    metric: MetricDefinition, labels: list[str], counts: list[int]
) -> dict:
    return {
        "backgroundColor": "transparent",
        "grid": {"top": 20, "right": 20, "bottom": 30, "left": 40},
        "xAxis": {
            "type": "category",
            "data": labels,
            "axisLabel": {"color": "#aaa", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#555"}},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {"color": "#aaa", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#333"}},
        },
        "series": [
            {
                "type": "bar",
                "data": counts,
                "itemStyle": {
                    "color": metric.color,
                    "borderRadius": [6, 6, 0, 0],
                },
                "barWidth": "50%",
            }
        ],
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "#333",
            "borderColor": "#555",
            "textStyle": {"color": "#fff"},
        },
    }


def _build_table_rows(labels: list[str], counts: list[int]) -> list[dict]:
    return [{"period": l, "count": c} for l, c in zip(labels, counts)]


def _render_chart(
    metric: MetricDefinition,
    logs: pd.DataFrame,
    freq: str,
    chart: ui.echart | None = None,
):
    tz = app.storage.user.get("tz", "US/Pacific")
    freqlbl = TIME_RANGE_LABEL[freq]
    if metric.value_type == "none":
        ui.label(f"Count by {freqlbl}").classes("text-h6 color-5 q-mb-sm")
        if chart is None:
            chart = ui.echart({}).classes("w-full").style("height: 250px")
        chart.options.clear()
        chart.options.update(
            _build_chart_options(metric, *_aggregate_none_metric(logs, freq, tz))
        )
    else:
        ui.image("/static/underconstruction.gif")
    return chart


def _render_table(metric: MetricDefinition, logs: pd.DataFrame):
    tz = app.storage.user.get("tz", "US/Pacific")
    if metric.value_type == "none":
        initial_labels, initial_counts = _aggregate_none_metric(logs, "W", tz)
        table = (
            ui.table(
                columns=[
                    {
                        "name": "period",
                        "label": "Period Ending On",
                        "field": "period",
                        "align": "left",
                    },
                    {
                        "name": "count",
                        "label": "Count",
                        "field": "count",
                        "align": "right",
                    },
                ],
                rows=_build_table_rows(initial_labels, initial_counts),
            )
            .props('flat hide-bottom :rows-per-page-options="[0]"')
            .classes("w-full")
        )


def detail_page(title, metric_id: int):
    ui.add_css(
        """
        .nicegui-content { align-items: stretch; }
        .time-range-btn { min-width: 48px; }
    """
    )
    tz = app.storage.user.get("tz", "US/Pacific")

    with closing(get_connection()) as conn:
        metric = get_metric_by_id(conn, metric_id)
        if not metric:
            title.text = "Not Found"
            ui.label("Metric not found.").classes("text-h6 color-8")
            return
        metric.id = cast(int, metric.id)
        logs = get_logs_for_metric(conn, metric.id, tz)

    title.text = metric.name

    # --- Time range toggle ---
    time_range = (
        ui.toggle({r: r for r in TIME_RANGES}, value="W")
        .props(
            "spread no-caps color=grey-8 text-color=grey-4 toggle-color=teal toggle-text-color=white"
        )
        .classes("full-width q-mb-md")
    )

    # --- Chart card ---
    with ui.card().classes("q-mb-md w-full"):
        with ui.card_section().classes("w-full"):
            chart = _render_chart(metric, logs, "W")

    # --- Data table ---
    with ui.card().classes("w-full"):
        with ui.card_section().classes("w-full"):
            table = _render_table(metric, logs)

    # --- Reactivity: update chart + table on time range change ---
    def on_time_range_change(e):
        tr = e.value
        _render_chart(metric, logs, tr, chart)
        # chart_title.text = f"Count by {TIME_RANGE_LABEL.get(tr, 'Day')}"
        # labels, counts = _aggregate_none_metric(logs, tr, tz)
        # new_opts = _build_chart_options(metric, labels, counts)
        # chart.options.clear()
        # chart.options.update(new_opts)
        # table.rows = _build_table_rows(labels, counts)
        _render_table()

    time_range.on_value_change(on_time_range_change)
