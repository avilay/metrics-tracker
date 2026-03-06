import os

from nicegui import app, ui

from app.components.layout import add_firebase_head_html
from app.errors import DemoUserNotFound
from app.repositories import get_connection
from app.repositories.user_repo import get_user_by_firebase_uid


@ui.page("/welcome")
def welcome_page():
    # If already authenticated, redirect to dashboard
    if app.storage.user.get("user_id"):
        ui.navigate.to("/")
        return

    add_firebase_head_html()
    ui.dark_mode(True)

    with ui.column().classes("absolute-center items-center gap-6"):
        with ui.card().classes("q-pa-lg items-center").style(
            "min-width: 350px; background: #1e1e1e"
        ):
            ui.icon("bar_chart", size="64px", color="teal")
            ui.label("Metrics Tracker").classes("text-h4 text-white q-mt-sm")
            ui.label("Track what matters. See your trends.").classes(
                "text-subtitle1 text-grey-5 q-mb-md"
            )

            ui.button(
                "Sign in with Google",
                icon="img:https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg",
                on_click=lambda: ui.run_javascript("upgradeToGoogle()"),
            ).props("unelevated color=white text-color=dark").classes(
                "full-width q-mb-sm"
            )

            ui.button(
                "Use Without Account",
                icon="no_accounts",
                on_click=lambda: ui.run_javascript("anonymousSignIn()"),
            ).props("outline color=teal").classes("full-width q-mb-sm")

            def demo_sign_in():
                conn = get_connection()
                try:
                    user = get_user_by_firebase_uid(
                        conn, os.environ["DEMO_FIREBASE_UID"]
                    )
                finally:
                    conn.close()
                if user is not None:
                    storage = app.storage.user
                    storage["user_id"] = user.id
                    storage["firebase_uid"] = user.firebase_uid
                    storage["is_anonymous"] = False
                    storage["display_name"] = "Demo User"
                    storage["photo_url"] = None
                    storage["is_demo"] = True
                    ui.navigate.to("/")
                else:
                    raise DemoUserNotFound()

            ui.button(
                "Try Demo",
                icon="play_arrow",
                on_click=demo_sign_in,
            ).props(
                "outline color=grey-5"
            ).classes("full-width")
