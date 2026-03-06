from nicegui import app, ui

from app.components.layout import page_layout
from app.database import get_connection
from app.models import MetricDefinition
from app.repositories.metric_repo import create_metric

VALUE_TYPE_OPTIONS = ["Numeric", "Categorical", "None"]
VALUE_TYPE_MAP = {"Numeric": "numeric", "Categorical": "categorical", "None": "none"}


@ui.page("/metric/new")
def add_metric_page():
    ui.dark_mode(True)
    page_layout("Add Metric")

    labels: list[str] = []

    with ui.column().classes("w-full q-pa-md"):
        ui.label("Add a New Metric").classes("text-h5 text-white q-mb-md")

        name_input = ui.input(label="Metric Name").props("filled dark").classes("w-full q-mb-md")

        value_type_select = ui.select(
            label="Value Type",
            options=VALUE_TYPE_OPTIONS,
            value="None",
        ).props("filled dark").classes("w-full q-mb-md")

        # Unit field (visible only for Numeric)
        unit_container = ui.column().classes("w-full q-mb-md")
        unit_container.bind_visibility_from(
            value_type_select, "value", backward=lambda v: v == "Numeric"
        )
        with unit_container:
            unit_input = ui.input(label="Unit (e.g., lbs, mg/dL)").props("filled dark").classes("w-full")

        # Labels field (visible only for Categorical)
        labels_container = ui.column().classes("w-full q-mb-md")
        labels_container.bind_visibility_from(
            value_type_select, "value", backward=lambda v: v == "Categorical"
        )
        with labels_container:
            ui.label("Allowed Labels").classes("text-subtitle2 text-grey q-mb-sm")
            with ui.row().classes("w-full items-center q-mb-sm"):
                label_input = ui.input(label="Add a label").props("filled dark").classes("flex-grow")
                add_label_btn = ui.button(icon="add", color="teal").props("round")

            chips_container = ui.row().classes("w-full q-gutter-sm")

        def rebuild_chips():
            chips_container.clear()
            with chips_container:
                for label_text in labels:
                    ui.chip(
                        label_text,
                        removable=True,
                        color="teal",
                        on_click=lambda e, lt=label_text: remove_label(lt),
                    ).on("remove", lambda e, lt=label_text: remove_label(lt))

        def add_label():
            text = label_input.value.strip() if label_input.value else ""
            if not text or text in labels:
                return
            labels.append(text)
            label_input.value = ""
            rebuild_chips()

        def remove_label(text: str):
            if text in labels:
                labels.remove(text)
                rebuild_chips()

        add_label_btn.on_click(add_label)
        label_input.on("keydown.enter", lambda e: add_label())

        # Properties placeholder
        ui.separator().classes("q-my-md")
        ui.label("Properties").classes("text-h6 text-white q-mb-sm")
        ui.label("Coming soon").classes("text-grey")

        # Error label
        error_label = ui.label("").classes("text-negative q-mt-md")
        error_label.set_visibility(False)

        def handle_create():
            # Validate
            name = name_input.value.strip() if name_input.value else ""
            vtype = value_type_select.value

            if not name:
                error_label.text = "Metric name is required."
                error_label.set_visibility(True)
                return

            if not vtype:
                error_label.text = "Value type is required."
                error_label.set_visibility(True)
                return

            db_vtype = VALUE_TYPE_MAP[vtype]

            unit = None
            categories: list[str] = []

            if vtype == "Numeric":
                unit = unit_input.value.strip() if unit_input.value else ""
                if not unit:
                    error_label.text = "Unit is required for numeric metrics."
                    error_label.set_visibility(True)
                    return

            if vtype == "Categorical":
                if not labels:
                    error_label.text = "At least one label is required for categorical metrics."
                    error_label.set_visibility(True)
                    return
                categories = list(labels)

            error_label.set_visibility(False)

            user_id = app.storage.user.get("user_id")
            metric = MetricDefinition(
                id=None,
                user_id=user_id,
                name=name,
                value_type=db_vtype,
                unit=unit if unit else None,
                categories=categories,
                properties=[],
            )

            conn = get_connection()
            try:
                create_metric(conn, metric)
            finally:
                conn.close()

            ui.navigate.to("/")

        ui.button("Create Metric", on_click=handle_create, color="teal").classes("q-mt-lg")
