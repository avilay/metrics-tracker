import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd

    return (pd,)


@app.cell
def _(pd):
    now = pd.Timestamp.now("US/Pacific")
    now
    return (now,)


@app.cell
def _(now):
    window_start = now.normalize().replace(day=1)
    window_start
    return (window_start,)


@app.cell
def _(now, pd, window_start):
    dtrange = pd.date_range(window_start, now, freq="W")
    dtrange
    return (dtrange,)


@app.cell
def _(dtrange, pd):
    df = pd.DataFrame({
        "recorded_at": dtrange,
        "value": [0] * len(dtrange),
    })
    df
    return (df,)


@app.cell
def _(df):
    df.info()
    return


@app.cell
def _(df):
    df.index
    return


@app.cell
def _(df):
    df
    return


@app.cell
def _(df):
    df.values
    return


@app.cell
def _(df):
    df.index
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
