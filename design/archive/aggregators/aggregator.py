# flake8: noqa: E731
from enum import Enum, StrEnum, auto
from typing import Callable, NamedTuple, override

import humanize
import pandas as pd
from nicegui import ui

from metrics_tracker.models import MetricDefinition


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


class AggregateFunction(Enum):
    SUM = auto()
    AVG = auto()
    COUNT = auto()


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

    def refresh(self, duration: Duration, func: AggregateFunction):
        print(f"Refreshing for duration :{duration}")
        self.aggregate(duration, func)
        self._update_chart()
        self._update_table()

    def _update_chart(self):
        raise NotImplementedError()

    def _update_table(self):
        raise NotImplementedError()

    def _table_cols(self) -> list[dict[str, str]]:
        raise NotImplementedError()

    def aggregate(self, duration: Duration, func: AggregateFunction):
        raise NotImplementedError()


class UnderConstructionAggregator(Aggregator):
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str) -> None:
        super().__init__(metric, logs, tz)

    @override
    def render_chart(self, *args, **kwargs):
        ui.image("/static/underconstruction.gif")

    @override
    def render_table(self, *args, **kwargs):
        return

    @override
    def refresh(self, *args, **kwargs):
        return

    @override
    def aggregate(self, *args, **kwargs):
        return
