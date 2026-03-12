import pandas as pd

from metrics_tracker.aggregators.aggregator import (
    Aggregator,
    UnderConstructionAggregator,
)
from metrics_tracker.aggregators.none_aggregator import NoneAggregator
from metrics_tracker.aggregators.numeric_aggregator import NumericAggregator
from metrics_tracker.models import MetricDefinition


def make_aggregator(
    metric: MetricDefinition, logs: pd.DataFrame, tz: str
) -> Aggregator:
    if metric.value_type == "none":
        return NoneAggregator(metric, logs, tz)
    elif metric.value_type == "numeric":
        return NumericAggregator(metric, logs, tz)
    else:
        return UnderConstructionAggregator(metric, logs, tz)
