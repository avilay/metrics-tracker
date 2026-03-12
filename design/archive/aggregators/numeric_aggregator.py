from typing import cast, override

import pandas as pd

from metrics_tracker.aggregators.aggregator import (
    AggregateFunction,
    Aggregator,
    Duration,
)
from metrics_tracker.models import MetricDefinition


class NumericAggregator(Aggregator):
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str) -> None:
        super().__init__(metric, logs, tz)
        self.ts_labels: list[str] = []
        self.values: list[float] = []
        self.func: AggregateFunction | None = None

    def aggregate(self, duration: Duration, func: AggregateFunction) -> None:
        if func not in (
            AggregateFunction.COUNT,
            AggregateFunction.SUM,
            AggregateFunction.AVG,
        ):
            raise ValueError(
                f"Cannot aggregate NumericAggregator with {func}. Only {Aggregator.COUNT}, {Aggregator.SUM}, and {Aggregator.AVG} will work."
            )

        self.func = func
        gst = self._calc_groupby_state(duration)
        filtered = self.logs[self.logs["recorded_at"] >= gst.window_start]
        if filtered.empty:
            self.ts_labels = [gst.ts_formatter(ts) for ts in gst.full_range]
            self.values = [0.0] * len(self.ts_labels)
        else:
            grouped = filtered.resample(gst.freq, on="recorded_at")
            if func == AggregateFunction.COUNT:
                grouped = grouped.size()
            elif func == AggregateFunction.SUM:
                grouped = grouped.sum()
            elif func == AggregateFunction.AVG:
                grouped = grouped.mean()

            grouped = grouped.reindex(gst.full_range, fill_value=0)
            grouped = cast(pd.DataFrame, grouped)
            self.ts_labels = [gst.ts_formatter(ts) for ts in grouped.index]
            self.ts_values = cast(list[float], grouped.values.tolist())

    @override
    def _table_cols(self):
        return [
            {
                "name": "period",
                "label": "Period Ending on",
                "field": "period",
                "align": "left",
            },
            {
                "name": func.value,
            },
        ]
