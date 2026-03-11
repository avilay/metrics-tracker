from contextlib import closing

from nicegui import app, ui

from metrics_tracker.repositories.metric_repo import (
    get_logs_for_metric,
    get_metric_by_id,
)
from metrics_tracker.utils import Duration, create_aggregator, get_connection


def detail_page(title: ui.label, metric_id: int):
    ui.add_css(
        """
    .nicegui-content { align-items: stretch; }
    .time-range-btn { min-width: 48x; }           
"""
    )

    tz = app.storage.user["tz"]
    print(f"Client timezone is {tz}")

    with closing(get_connection()) as conn:
        metric = get_metric_by_id(conn, metric_id)
        if not metric:
            ui.notify(f"Metric with id {metric_id} does not exist!", type="warning")
            ui.navigate.to("/")
            return

        logs = get_logs_for_metric(conn, metric_id, tz)
        if logs is None or logs.empty:
            ui.label("TODO: Show better UI for no logs")
            return

    agg = create_aggregator(metric, logs, tz)
    agg.aggregate(Duration.WEEK)

    ui.toggle([d.value for d in [*Duration]], value=Duration.WEEK).props(
        "spread no-caps color=grey-8 text-color=grey-4 toggle-color=teal toggle-text-color=white"
    ).classes("full-width q-mb-md").on_value_change(
        lambda e: agg.refresh(Duration(e.value))
    )

    # Chart card
    with ui.card().classes("q-mb-md w-full"):
        with ui.card_section().classes("w-full"):
            agg.render_chart(Duration.WEEK)

    # Table card
    with ui.card().classes("w-full"):
        with ui.card_section().classes("w-full"):
            agg.render_table(Duration.WEEK)
