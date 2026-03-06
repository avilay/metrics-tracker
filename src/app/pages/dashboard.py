from nicegui import app, ui


def dashboard_page():
    print(app.storage.user)
    with ui.column().classes("w-full q-pa-md"):
        ui.label("Your Metrics").classes("text-h5 text-white")
        ui.label("No metrics yet. Add one to get started!").classes(
            "text-subtitle1 text-grey"
        )

    ui.button(icon="add", on_click=lambda: ui.navigate.to("/metric/new")).props(
        "fab color=teal"
    ).classes("fixed bottom-4 right-4")
