from nicegui import app, ui


def account_page():
    user_data = app.storage.user
    display_name = user_data.get("display_name", "Anonymous")
    email = user_data.get("email", "")
    photo_url = user_data.get("photo_url")

    with ui.column().classes("w-full q-pa-md items-center"):
        if photo_url:
            with ui.element("q-avatar").props("size=80px"):
                ui.image(photo_url)
        else:
            ui.icon("account_circle", size="80px", color="grey")

        ui.label(display_name).classes("text-h5 text-white q-mt-md")
        if email:
            ui.label(email).classes("text-subtitle1 text-grey")
