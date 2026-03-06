from nicegui import app, ui


def new_metric_page():
    print(app.storage.user)
    ui.label("NEW METRIC")
