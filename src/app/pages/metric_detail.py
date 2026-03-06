from nicegui import ui


def metric_detail_page(metric_id: int):
    with ui.column().classes("w-full q-pa-md"):
        ui.label(f"Metric #{metric_id}").classes("text-h5 text-white")
        ui.label("Coming in Phase 3").classes("text-subtitle1 text-grey")
