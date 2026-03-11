# Metric Detail Page — Implementation Plan (value_type = "none")

## Overview

A new sub-page at `/metric/{metric_id}` that shows aggregated log data for a single metric with `value_type == "none"`. The page has three sections: time-range selector, bar chart, and data table. The user can toggle between D/W/M/6M/Y to change the time window and aggregation granularity.

## Time Range Logic

All ranges are anchored to "now" in the user's timezone (hardcoded `US/Pacific` for now, matching dashboard).

| Button | Window start | Resample freq | X-axis labels |
|--------|-------------|---------------|---------------|
| D | Start of today (midnight) | Hourly (`"h"`) | Hour labels (e.g., "6 AM", "7 AM") |
| W | Start of current week (Monday) | Daily (`"D"`) | Day labels (e.g., "Mon", "Tue") |
| M | Start of current month (1st) | Weekly (`"W"`) | Week labels (e.g., "Week 1", "Week 2") |
| 6M | 1st of the month 6 months back (count current month as -1) | Monthly (`"MS"`) | Month labels (e.g., "Oct", "Nov") |
| Y | Start of current year (Jan 1) | Monthly (`"MS"`) | Month labels (e.g., "Jan", "Feb") |

For a "none" value-type metric, the aggregate function is always **count** (number of log entries in each bucket). This uses `resample(...).size()` as demonstrated in the analysis notebook.

### 6M calculation example

Today is March 10. March is -1, Feb is -2, Jan is -3, Dec is -4, Nov is -5, Oct is -6. So the window starts at Oct 1.

## Files to Create/Modify

### 1. `src/metrics_tracker/pages/detail.py` (new)

The page function `detail_page(title, metric_id: int)`.

**Data loading:**
- Fetch `MetricDefinition` via `get_metric_by_id(conn, metric_id)`
- Fetch logs via `get_logs_for_metric(conn, metric_id, tz)` — returns a DataFrame with `recorded_at` column
- Filter the DataFrame to the selected time window
- Resample and count

**UI structure (matching the mockup):**
- Header: back button (navigates to `/`) + metric name as title
- Time-range button group (D/W/M/6M/Y) — Quasar `q-btn-group` via NiceGUI
- ECharts bar chart inside a card
- Data table inside a card showing Period + Count columns

**Reactivity:**
- Time range selection is a reactive `ui.toggle` or button group
- On change, recompute the filtered/resampled data and update the chart + table
- Use `chart.update()` for ECharts and rebuild the table rows

### 2. `src/metrics_tracker/pages/__init__.py` (modify)

Add `from .detail import detail_page` to the imports.

### 3. `src/main.py` (modify)

Add the detail page route to `ui.sub_pages()`:
```python
"/metric/{metric_id}": detail_page,
```

NiceGUI sub-pages support path parameters — the `metric_id` will be passed as a keyword argument to the page function.

### 4. `src/metrics_tracker/pages/dashboard.py` (modify)

Make each metric card clickable to navigate to the detail page:
```python
ui.navigate.to(f"/metric/{metric.id}")
```

The card already has `classes("cursor-pointer")` — just wire up the `on_click`.

## Aggregation Helper

Inside `detail.py`, create a helper function:

```python
def aggregate_none_metric(
    logs: pd.DataFrame, time_range: str, tz: str
) -> tuple[list[str], list[int]]:
    """
    Returns (labels, counts) for the bar chart and table.
    """
```

This function will:
1. Compute the window start based on `time_range` and current time
2. Filter `logs` to `recorded_at >= window_start`
3. Generate the full date range for the window (so empty buckets show as 0)
4. Resample using `.size()` and `.reindex(full_range, fill_value=0)`
5. Format the index into human-readable labels

## Implementation Steps

1. **Create `detail.py`** with the aggregation helper and the page function. Start with the data logic (aggregation) and a minimal UI that displays the chart and table for a hardcoded time range (W).

2. **Wire up routing** — add the sub-page route in `main.py` and import in `__init__.py`.

3. **Add navigation from dashboard** — make metric cards clickable.

4. **Add time-range toggle** — make it reactive so switching D/W/M/6M/Y re-aggregates and updates the chart and table.

5. **Polish** — match the mockup's styling (dark cards, teal accents, chart colors using the metric's stored color).

## Notes

- The mockup uses a FAB button to log entries. **Skip the log-entry modal for now** — that will be a separate task.
- The mockup uses the metric's purple color for chart bars. Use `metric.color` from the DB.
- Reuse the same ECharts patterns from `dashboard.py` (sparklines) but with axis labels shown.
- The header back button should use `ui.navigate.to("/")` to return to the dashboard.
