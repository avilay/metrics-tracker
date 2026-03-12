import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from metrics_tracker.utils import get_connection
    from contextlib import closing
    from metrics_tracker.repositories.metric_repo import get_logs_for_metric
    import pandas as pd
    from dotenv import load_dotenv
    import os
    from pathlib import Path
    from enum import StrEnum
    import humanize

    return closing, get_connection, get_logs_for_metric, load_dotenv, os, pd


@app.cell
def _(load_dotenv):
    load_dotenv()
    return


@app.cell
def _(os):
    DB_PATH = os.environ["DB_PATH"]
    return (DB_PATH,)


@app.cell
def _(DB_PATH, closing, get_connection, get_logs_for_metric):
    with closing(get_connection(DB_PATH)) as conn:
        meditate = get_logs_for_metric(conn, 3, "US/Pacific")
        weight = get_logs_for_metric(conn, 5, "US/Pacific")
        mood = get_logs_for_metric(conn, 1, "US/Pacific")
    return (mood,)


@app.cell
def _(mood):
    mood
    return


@app.cell
def _(mood, pd):
    agg = mood.groupby([pd.Grouper(key="recorded_at", freq="W"), "value"]).size()
    agg
    return (agg,)


@app.cell
def _(agg):
    agg.index
    return


@app.cell
def _(agg, pd):
    isinstance(agg.index, pd.MultiIndex)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
