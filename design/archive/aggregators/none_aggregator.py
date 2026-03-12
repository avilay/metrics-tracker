from typing import cast, override

import pandas as pd

from metrics_tracker.aggregators.aggregator import (
    AggregateFunction,
    Aggregator,
    Duration,
)
from metrics_tracker.models import MetricDefinition


class NoneAggregator(Aggregator):
    def __init__(self, metric: MetricDefinition, logs: pd.DataFrame, tz: str) -> None:
        super().__init__(metric, logs, tz)
        self.ts_labels: list[str] = []
        self.counts: list[int] = []

    def aggregate(self, duration: Duration, func: AggregateFunction):
        if func != AggregateFunction.COUNT:
            raise ValueError(
                f"Cannot aggregate NoneAggregator with {func}. The only function that will work is {AggregateFunction.COUNT}"
            )
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
            grouped = cast(pd.DataFrame, grouped)
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
