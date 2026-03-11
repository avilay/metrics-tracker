from contextlib import closing
from datetime import datetime, timedelta
from typing import Tuple, cast

import humanize
import pandas as pd
import pytz
from nicegui import app, ui

from metrics_tracker.models import MetricDefinition
from metrics_tracker.repositories.metric_repo import (
    get_logs_for_metric,
    get_metrics_for_user,
)
from metrics_tracker.utils import get_connection


def _render_sparklines(metric: MetricDefinition, logs: pd.DataFrame) -> None:
    if logs is None or logs.empty:
        with ui.row().classes("items-center"):
            ui.icon("bar_chart", size="32px").classes("color-8")
            ui.label("No logs yet").classes("text-subtitle1 color-8 q-ml-xs")
        return

    today = pd.Timestamp.now(tz="US/Pacific").normalize()
    one_week_ago = today - pd.DateOffset(days=6)
    all_days = pd.date_range(one_week_ago, today, freq="D")
    recent_logs = logs[logs["recorded_at"] >= one_week_ago]

    data = []
    if metric.value_type == "none":
        print(f"Rendering sparklines for {metric.name} ({metric.color})")
        daily_counts = (
            recent_logs.resample("D", on="recorded_at")
            .size()
            .reindex(all_days, fill_value=0)
        )
        data = daily_counts.values.tolist()
    elif metric.value_type == "numeric":
        print(f"Rendering sparklines for {metric.name} ({metric.color})")
        daily_avg = (
            recent_logs.resample("D", on="recorded_at")
            .mean()
            .dropna()
            .reindex(all_days, fill_value=0)
        )
        print(daily_avg)
        data = daily_avg["value"].values.tolist()
    elif metric.value_type == "categorical":
        print(f"Rendering sparklines for {metric.name} ({metric.color})")
        last_value = logs.tail(1).values[0][1]
        daily_counts = (
            recent_logs[recent_logs["value"] == last_value]
            .resample("D", on="recorded_at")
            .size()
            .reindex(all_days, fill_value=0)
        )
        data = daily_counts.values.tolist()
    print(data)
    chart = ui.echart(
        {
            "grid": {"top": 5, "right": 5, "bottom": 5, "left": 5},
            "xAxis": {
                "type": "category",
                "show": False,
                "data": list(range(len(data))),
            },
            "yAxis": {"type": "value", "show": False},
            "series": [
                {
                    "type": "bar",
                    "data": data,
                    "itemStyle": {"color": metric.color, "borderRadius": [4, 4, 0, 0]},
                    "barWidth": "60%",
                }
            ],
        }
    )
    chart.classes("w-full").style("height: 80px")


def _card_content(metric: MetricDefinition, logs: pd.DataFrame) -> Tuple[str, str]:
    if metric.value_type == "none":
        weekly_counts = logs.resample("W", on="recorded_at").size()
        last_weekly_count = weekly_counts.values[-1].item()
        return f"{last_weekly_count}x", "this week"
    elif metric.value_type == "numeric":
        last_reading = logs.tail(1).values[0][1]
        return str(last_reading), str(metric.unit)
    elif metric.value_type == "categorical":
        last_reading = logs.tail(1).values[0][1]
        weekly_counts = (
            logs[logs["value"] == last_reading].resample("W", on="recorded_at").size()
        )
        last_weekly_count = weekly_counts.values[-1].item()
        return last_reading, f"{last_weekly_count}x this week"
    else:
        raise RuntimeError(f"Unkonwn metric type {metric.value_type}")


def _render_card(metric: MetricDefinition, logs: pd.DataFrame):
    last_recorded_at_lbl, headline, byline = "", "", ""

    # TODO: Get the user's timezone
    browser_tz = "US/Pacific"
    tz = pytz.timezone(browser_tz)

    if logs is not None and not logs.empty:
        last_recorded_at = logs.tail(1).values[0][0].to_pydatetime()
        # last_recorded_at_lbl = last_recorded_at.strftime("%a, %b %d, %Y %I:%M %p")
        if datetime.now().astimezone(tz) - last_recorded_at < timedelta(days=1):
            last_recorded_at_lbl = humanize.naturaltime(last_recorded_at)
        else:
            last_recorded_at_lbl = humanize.naturaldate(last_recorded_at)
        headline, byline = _card_content(metric, logs)

    with ui.card(align_items="stretch").on(
        "click", lambda: ui.navigate.to(f"/metric/{metric.id}")
    ).classes("cursor-pointer metric-card"):
        with ui.card_section().classes("q-pb-none"):
            ui.label(metric.name).classes("text-subtitle1 color-4")
            with ui.row().classes("q-mt-sm items-center"):
                ui.label(headline).classes("text-h4 text-weight-bold")
                ui.label(byline).classes("text-subtitle1 color-5 q-ml-xs")
            ui.label(last_recorded_at_lbl).classes("text-caption color-6 q-mt-xs")
        with ui.card_section().classes("q-pt-none q-pb-none"):
            _render_sparklines(metric, logs)


def dashboard_page(title):
    title.text = "Metrics Tracker"
    ui.add_css(
        """
        .nicegui-content {align-items: stretch;}
        .metric-card { transition: transform 0.15s; }
        .metric-card:hover { transform: scale(1.02); }
    """
    )

    user_id = app.storage.user["user_id"]
    data: list[tuple[MetricDefinition, pd.DataFrame]] = []
    with closing(get_connection()) as conn:
        metrics = get_metrics_for_user(conn, user_id)
        for metric in metrics:
            metric.id = cast(int, metric.id)
            logs = get_logs_for_metric(conn, metric.id, "US/Pacific")
            data.append((metric, logs))

    if not data:
        with ui.column().classes("w-full items-center q-pa-xl"):
            ui.icon("bar_chart", size="64px", color="grey-8")
            ui.label("No metrics yet").classes("text-h6 color-8 q-mt-md")
            ui.label("Tap + to add your first metric").classes("text-body2 color-8")
    else:
        with ui.grid(columns="repeat(auto-fit, minmax(350px, 1fr))").classes(
            "w-full justify-center"
        ):
            for metric, logs in data:
                _render_card(metric, logs)

    ui.button(icon="add", on_click=lambda: ui.navigate.to("/metric/new")).props(
        "fab color=secondary"
    ).classes("fixed bottom-4 right-4")
