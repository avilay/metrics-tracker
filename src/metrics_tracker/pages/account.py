from nicegui import app, ui

# from metrics_tracker.components.layout import page_layout


# @ui.page("/account")
def account_page(title):
    # if not app.storage.user.get("user_id"):
    #     ui.navigate.to("/welcome")
    #     return

    # page_layout("Account")
    title.text = "Account"
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

        ui.label(display_name).classes("text-h5 q-mt-md")
        if email:
            ui.label(email).classes("text-subtitle1")
