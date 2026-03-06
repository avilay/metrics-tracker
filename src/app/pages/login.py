from nicegui import ui

from app.components.layout import add_firebase_head_html


def login_page():
    add_firebase_head_html()
    with ui.card().classes("absolute-center"):
        ui.label("Metrics Tracker").classes("text-h4 q-mb-md")
        ui.label("Sign in to track your metrics").classes("text-subtitle1 q-mb-lg")
        ui.button(
            "Sign in with Google",
            on_click=lambda: ui.run_javascript("upgradeToGoogle()"),
        ).props("color=primary").classes("full-width")
