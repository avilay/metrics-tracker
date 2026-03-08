from nicegui import ui

# from metrics_tracker.components.layout import page_layout


# @ui.page("/")
def dashboard_page(title):
    # if not app.storage.user.get("user_id"):
    #     ui.navigate.to("/welcome")
    #     return

    # page_layout("Metrics Tracker")
    title.text = "Metrics Tracker"
    with ui.column().classes("w-full q-pa-md"):
        ui.label("This is the home page content.")

    ui.button(icon="add", on_click=lambda: ui.navigate.to("/metric/new")).props(
        "fab color=secondary"
    ).classes("fixed bottom-4 right-4")
