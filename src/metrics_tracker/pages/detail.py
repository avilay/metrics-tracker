from contextlib import closing
from enum import StrEnum
from typing import Any, cast

import humanize
import pandas as pd
from nicegui import app, ui

from metrics_tracker.models import MetricDefinition
from metrics_tracker.repositories.metric_repo import (
    get_logs_for_metric,
    get_metric_by_id,
)
from metrics_tracker.utils import get_connection


class Duration(StrEnum):
    DAY = "D"
    WEEK = "W"
    MONTH = "M"
    SIX_MONTHS = "6M"
    YEAR = "Y"


duration_freq_label: dict[Duration, tuple[str, str]] = {
    Duration.DAY: ("h", "Hour"),
    Duration.WEEK: ("D", "Day"),
    Duration.MONTH: ("W", "Week"),
    Duration.SIX_MONTHS: ("MS", "Month"),
    Duration.YEAR: ("MS", "Month"),
}


class ApplyFunc(StrEnum):
    COUNT = "count"
    SUM = "total"
    MEAN = "average"


class Apply(StrEnum):
    COUNT = "Count"
    SUM = "Total"
    MEAN = "Average"


class Aggregator:
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str):
        self.metric = metric
        self.logs = logs
        self.tz = tz
        self.now = pd.Timestamp.now(tz=tz)

        self.duration = Duration.WEEK
        self.filters: list[tuple[str, str]] = []
        self.splitby = "value" if metric.value_type == "categorical" else ""
        self.apply = ApplyFunc.COUNT

        self.df = logs

    def aggregate(self):
        freq = duration_freq_label[self.duration][0]

        if self.duration == Duration.DAY:
            window_start = self.now.normalize()
            full_range = pd.date_range(window_start, self.now, freq=freq)
            ts_fmt = humanize.naturaltime
        elif self.duration == Duration.WEEK:
            window_start = self.now.normalize() - pd.DateOffset(days=self.now.dayofweek)
            full_range = pd.date_range(window_start, self.now, freq=freq)
            ts_fmt = humanize.naturalday
        elif self.duration == Duration.MONTH:
            window_start = self.now.normalize().replace(day=1)
            full_range = pd.date_range(
                window_start, self.now + pd.Timedelta(days=6), freq=freq
            )
            ts_fmt = humanize.naturaldate
        elif self.duration == Duration.SIX_MONTHS:
            # Go back 6 months (current month is -1)
            month = self.now.month - 6  # e.g., March(3) - 6 = -3
            year = self.now.year
            if month <= 0:
                month += 12
                year -= 1
            window_start = pd.Timestamp(year=year, month=month, day=1, tz=self.now.tz)
            full_range = pd.date_range(window_start, self.now, freq=freq)
            ts_fmt = lambda ts: ts.strftime("%b")  # noqa: E731
        elif self.duration == Duration.YEAR:
            window_start = pd.Timestamp(
                year=self.now.year, month=1, day=1, tz=self.now.tz
            )
            full_range = pd.date_range(window_start, self.now, freq=freq)
            ts_fmt = lambda ts: ts.strftime("%b")  # noqa: E731
        else:
            raise RuntimeError("KA-BOOM!!")

        filtered = self.logs[self.logs["recorded_at"] > window_start]

        if filtered.empty:
            data = {
                "recorded_at": full_range,
                "ts": [ts_fmt(ts) for ts in full_range],
                "value": [0] * len(full_range),
            }
            for cat in self.metric.categories:
                data[cat] = [0] * len(full_range)
            df = pd.DataFrame(data)
            df = df.set_index("recorded_at")
            self.df = df
            return

        if self.splitby:
            splits = filtered.groupby(
                [pd.Grouper(key="recorded_at", freq=freq), self.splitby]
            )
        else:
            splits = filtered.resample(freq, on="recorded_at")

        if self.apply == ApplyFunc.COUNT:
            splits = splits.size()
        elif self.apply == ApplyFunc.SUM:
            splits = splits.sum()
        elif self.apply == ApplyFunc.MEAN:
            splits = splits.mean()
        else:
            raise RuntimeError("KA-BOOM!!")

        splits = cast(pd.DataFrame, splits)
        if isinstance(splits.index, pd.MultiIndex):
            splits = splits.unstack(fill_value=0)
            # Ensure all categories are present as columns
            for cat in self.metric.categories:
                if cat not in splits.columns:
                    splits[cat] = 0
            splits = splits[self.metric.categories]  # reorder to match definition order

        splits = cast(pd.DataFrame, splits)
        combined = splits.reindex(full_range, fill_value=0)
        if isinstance(combined, pd.Series):
            combined = combined.to_frame("value")
        combined.insert(0, "ts", combined.index.map(ts_fmt))
        print("Final dataframe:")
        print(combined)
        self.df = combined

    @property
    def table_columns(self) -> list[dict[str, str]]:
        columns = self.df.columns.values.tolist()
        colinfo = [
            {
                "name": "period",
                "label": "Period Ending On",
                "field": "period",
                "align": "left",
            }
        ]
        for column in columns[1:]:
            name = self.apply.value if column == "value" else column
            colinfo.append(
                {
                    "name": name,
                    "label": name.capitalize(),
                    "field": name,
                    "align": "right",
                }
            )

        return colinfo

    @property
    def table_rows(self) -> list[dict[str, Any]]:
        allrows = []
        cols = self.df.columns.values.tolist()
        for row in self.df.values:
            rowinfo = {"period": row[0]}
            for colidx, cell in enumerate(row[1:], start=1):
                fldname = self.apply.value if cols[colidx] == "value" else cols[colidx]
                rowinfo[fldname] = cell
            allrows.append(rowinfo)
        return allrows


def set_table(agg: Aggregator, table: ui.table):
    table.columns = agg.table_columns
    table.rows = agg.table_rows


CATEGORY_COLORS = [
    "#66bb6a",  # green
    "#42a5f5",  # blue
    "#ffa726",  # orange
    "#ef5350",  # red
    "#ab47bc",  # purple
    "#26c6da",  # cyan
    "#ffee58",  # yellow
    "#ec407a",  # pink
    "#5c6bc0",  # indigo
    "#29b6f6",  # light-blue
]


def set_chart(agg: Aggregator, chart: ui.echart):
    chart.options.clear()

    opts = {
        "backgroundColor": "transparent",
        "grid": {"top": 30, "right": 20, "bottom": 30, "left": 40},
        "xAxis": {
            "type": "category",
            "data": agg.df["ts"].values.tolist(),
            "axisLabel": {"color": "#aaa", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#555"}},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": {"color": "#aaa", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#333"}},
        },
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "#333",
            "borderColor": "#555",
            "textStyle": {"color": "#fff"},
        },
    }

    series = []
    columns = agg.df.columns.values.tolist()
    for i, column in enumerate(columns):
        is_last = i == len(columns)
        bar = {
            "name": column,
            "type": "bar",
            "data": agg.df[column].values.tolist(),
            "barWidth": "50%",
        }

        if column != "value":
            bar["stack"] = "categorical"
            bar["itemStyle"] = {
                "color": CATEGORY_COLORS[i % len(CATEGORY_COLORS)],
                **({"borderRadius": [6, 6, 0, 0]} if is_last else {}),
            }
        else:
            bar["itemStyle"] = {
                "color": agg.metric.color,
                "borderRadius": [6, 6, 0, 0],
            }

        series.append(bar)

    opts["series"] = series
    chart.options.update(opts)


def _chart_title(agg: Aggregator) -> str:
    period = duration_freq_label[agg.duration][1]
    if agg.metric.value_type == "categorical":
        return f"{agg.metric.name} Count by {period}"
    return f"{agg.apply.value.capitalize()} by {period}"


def detail_page(title: ui.label, metric_id: int):
    ui.add_css(
        """
    .nicegui-content { align-items: stretch; }
    .time-range-btn { min-width: 48x; }
"""
    )

    tz = app.storage.user["tz"]

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

    title.text = metric.name

    agg = Aggregator(metric, logs, app.storage.user["tz"])

    duration = (
        ui.toggle([d.value for d in [*Duration]], value=Duration.WEEK)
        .props(
            "spread no-caps color=grey-8 text-color=grey-4 toggle-color=teal toggle-text-color=white"
        )
        .classes("full-width q-mb-md")
    )

    aggfunc = ApplyFunc.MEAN if metric.value_type == "numeric" else ApplyFunc.COUNT
    func = (
        ui.select(
            [a.value.capitalize() for a in [*ApplyFunc]],
            value=aggfunc.value.capitalize(),
        )
        .bind_visibility_from(metric, "value_type", backward=lambda v: v == "numeric")
        .props(
            "spread no-caps color=grey-8 text-color=grey-4 toggle-color=teal toggle-text-color=white"
        )
        .classes("full-width q-mb-md")
    )
    agg.apply = aggfunc

    agg.aggregate()

    # Chart card
    with ui.card().classes("q-mb-md w-full"):
        with ui.card_section().classes("w-full"):
            title = ui.label(_chart_title(agg)).classes("text-h6 color-5 q-mb-sm")
            chart = ui.echart({}).classes("w-full").style("height: 250px")

    set_chart(agg, chart)

    # Table card
    with ui.card().classes("w-full"):
        with ui.card_section().classes("w-full"):
            table = (
                ui.table(columns=agg.table_columns, rows=agg.table_rows)
                .props('flat hide-bottom :rows-per-page-options="[0]"')
                .classes("w-full")
            )

    def handle_duration_change(e):
        agg.duration = Duration(e.value)
        agg.aggregate()
        title.text = _chart_title(agg)
        set_chart(agg, chart)
        set_table(agg, table)

    def handle_func_change(e):
        agg.apply = ApplyFunc(e.value.lower())
        agg.aggregate()
        title.text = _chart_title(agg)
        set_chart(agg, chart)
        set_table(agg, table)

    duration.on_value_change(handle_duration_change)
    func.on_value_change(handle_func_change)
