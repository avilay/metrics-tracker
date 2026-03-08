from nicegui import ui


def dummy_page(title):
    title.text = "Dummy"
    ui.add_css(".nicegui-content {align-items: flex-start;}")
    with ui.column().classes("w-full items-stretch"):
        ui.label("A Label").classes("text-h5 q-mb-md")
        ui.input(label="An Input").props("filled q-mb-md")
        ui.select(
            label="A Dropdown",
            options=["Up", "Down", "Strange", "Charm", "Top", "Bottom"],
            value="Up",
        ).props("filled").classes("w-full q-mb-md")
