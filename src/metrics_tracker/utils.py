import os
import sqlite3
from enum import StrEnum
from pathlib import Path
from typing import Callable, NamedTuple, cast, override

import humanize
import pandas as pd
from nicegui import app, ui

from metrics_tracker.models import MetricDefinition

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


class Duration(StrEnum):
    DAY = "D"
    WEEK = "W"
    MONTH = "M"
    SIX_MONTHS = "6M"
    YEAR = "Y"


class GroupByState(NamedTuple):
    window_start: pd.Timestamp
    full_range: pd.DatetimeIndex
    title_label: str
    ts_formatter: Callable[[pd.Timestamp], str]
    freq: str


class Aggregator:
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str) -> None:
        self.metric = metric
        self.logs = logs
        self.now = pd.Timestamp.now(tz=tz)
        self.chart: ui.echart | None = None
        self.table: ui.table | None = None

    def _calc_groupby_state(self, duration: Duration) -> GroupByState:
        if duration == Duration.DAY:
            window_start = self.now.normalize()
            title_label = "Hour"
            freq = "h"
            ts_formatter = humanize.naturaltime
        elif duration == Duration.WEEK:
            window_start = self.now.normalize() - pd.DateOffset(days=self.now.dayofweek)
            title_label = "Day"
            freq = "D"
            ts_formatter = humanize.naturalday
        elif duration == Duration.MONTH:
            window_start = self.now.normalize().replace(day=1)
            title_label = "Week"
            freq = "W"
            ts_formatter = humanize.naturaldate
        elif duration == Duration.SIX_MONTHS:
            # Go back 6 months (current month is -1)
            month = self.now.month - 6  # e.g., March(3) - 6 = -3
            year = self.now.year
            if month <= 0:
                month += 12
                year -= 1
            window_start = pd.Timestamp(year=year, month=month, day=1, tz=self.now.tz)
            title_label = "Month"
            freq = "MS"
            ts_formatter = lambda ts: ts.strftime("%b")
        elif duration == Duration.YEAR:
            window_start = pd.Timestamp(
                year=self.now.year, month=1, day=1, tz=self.now.tz
            )
            title_label = "Month"
            freq = "MS"
            ts_formatter = lambda ts: ts.strftime("%b")
        full_range = pd.date_range(window_start, self.now, freq=freq)
        return GroupByState(window_start, full_range, title_label, ts_formatter, freq)

    def render_chart(self, duration: Duration):
        self.chart = ui.echart({}).classes("w-full").style("height: 250px")
        self._update_chart()

    def render_table(self, duration: Duration):
        self.table = (
            ui.table(columns=self._table_cols(), rows=[])
            .props('flat hide-bottom :rows-per-page-options="[0]"')
            .classes("w-full")
        )
        self._update_table()

    def refresh(self, duration: Duration):
        print(f"Refreshing for duration :{duration}")
        self.aggregate(duration)
        self._update_chart()
        self._update_table()

    def _update_chart(self):
        raise NotImplementedError()

    def _update_table(self):
        raise NotImplementedError()

    def _table_cols(self) -> list[dict[str, str]]:
        raise NotImplementedError()

    def aggregate(self, duration: Duration):
        raise NotImplementedError()


class NoneAggregator(Aggregator):
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str) -> None:
        super().__init__(metric, logs, tz)
        self.ts_labels: list[str] = []
        self.counts: list[int] = []

    def aggregate(self, duration: Duration):
        gst = self._calc_groupby_state(duration)
        filtered = self.logs[self.logs["recorded_at"] >= gst.window_start]
        if filtered.empty:
            self.ts_labels = [gst.ts_formatter(ts) for ts in gst.full_range]
            self.counts = [0] * len(self.ts_labels)
        else:
            grouped = (
                filtered.resample(gst.freq, on="recorded_at")
                .size()
                .reindex(gst.full_range, fill_value=0)
            )
            self.ts_labels = [gst.ts_formatter(ts) for ts in grouped.index]
            self.counts = cast(list[int], grouped.values.tolist())
        print(f"Timestamps: {self.ts_labels}, {gst.full_range}")
        print(f"Counts: {self.counts}")

    @override
    def _update_table(self):
        if self.table is not None:
            self.table.rows = [
                {"period": lbl, "count": count}
                for lbl, count in zip(self.ts_labels, self.counts)
            ]

    @override
    def _table_cols(self):
        return [
            {
                "name": "period",
                "label": "Period Ending On",
                "field": "period",
                "align": "left",
            },
            {"name": "count", "label": "Count", "field": "count", "align": "right"},
        ]

    @override
    def _update_chart(self):
        if self.chart is not None:
            self.chart.options.clear()
            self.chart.options.update(
                {
                    "backgroundColor": "transparent",
                    "grid": {"top": 20, "right": 20, "bottom": 30, "left": 40},
                    "xAxis": {
                        "type": "category",
                        "data": self.ts_labels,
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
                            "data": self.counts,
                            "itemStyle": {
                                "color": self.metric.color,
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
            )


class UnderConstructionAggregator(Aggregator):
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str) -> None:
        super().__init__(metric, logs, tz)

    @override
    def render_chart(self, duration: Duration):
        ui.image("/static/underconstruction.gif")

    @override
    def render_table(self, duration: Duration):
        return

    @override
    def refresh(self, duration: Duration):
        return

    @override
    def aggregate(self, duration: Duration):
        return


def create_aggregator(
    metric: MetricDefinition, logs: pd.DataFrame, tz: str
) -> Aggregator:
    if metric.value_type == "none":
        return NoneAggregator(metric, logs, tz)
    else:
        return UnderConstructionAggregator(metric, logs, tz)
