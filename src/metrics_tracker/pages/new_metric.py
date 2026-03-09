from nicegui import app, ui

from metrics_tracker.models import MetricDefinition
from metrics_tracker.repositories import get_connection
from metrics_tracker.repositories.metric_repo import create_metric
import random

COLORS = [
    "red",
    "pink",
    "purple",
    "indigo",
    "blue",
    "light-blue",
    "cyan",
    "teal",
    "green",
    "light-green",
    "lime",
    "yellow",
    "amber",
    "orange",
    "deep-orange",
]


VALUE_TYPE_OPTIONS = ["Numeric", "Categorical", "None"]


def new_metric_page(title):
    title.text = "New Metric"
    ui.add_css(".nicegui-content {align-items: stretch;}")

    with ui.column().classes("w-full items-stretch"):
        ui.label("New Metric").classes("text-h5 q-mb-md")
        name_input = ui.input(label="Metric Name").props("filled q-mb-md")

        value_type_select = (
            ui.select(label="Value Type", options=VALUE_TYPE_OPTIONS, value="None")
            .props("filled")
            .classes("w-full q-mb-md")
        )

        # Unit field (visible only for Numeric)
        unit_container = ui.column().classes("w-full q-mb-md")
        unit_container.bind_visibility_from(
            value_type_select, "value", backward=lambda v: v == "Numeric"
        )
        with unit_container:
            unit_input = (
                ui.input(label="Unit (e.g., lbs, mg/dL)")
                .props("filled")
                .classes("w-full")
            )

        categories_input = ui.input_chips(
            "Allowed Categories", new_value_mode="add-unique"
        )

        # Properties placeholder
        ui.separator().classes("q-my-md")
        ui.label("Properties").classes("text-h6 text-white q-mb-sm")
        ui.label("Coming soon").classes("text-grey")

        def handle_create():
            # Validate
            name = name_input.value.strip() if name_input.value else ""
            vtype = value_type_select.value

            if not name:
                ui.notify("Metric name is required!", type="negative")
                return

            if not vtype:
                ui.notify("Value type is required!", type="negative")
                return

            unit = None
            vtype = vtype.strip().lower()
            categories = categories_input.value

            if vtype == "numeric":
                unit = unit_input.value.strip() if unit_input.value else ""
                if not unit:
                    ui.notify("Unit is required for numeric metrics!", type="negative")
                    return

            if vtype == "categorical":
                if len(categories) < 2:
                    ui.notify(
                        "At least 2 labels are required for categorical metrics!",
                        type="negative",
                    )
                    return

            user_id = app.storage.user["user_id"]
            metric = MetricDefinition(
                id=None,
                user_id=user_id,
                name=name,
                value_type=vtype,
                color=random.choice(COLORS),
                unit=unit or None,
                categories=categories,
                properties=[],
            )
            conn = get_connection()
            try:
                create_metric(conn, metric)
            finally:
                conn.close()

            ui.navigate.to("/")

        ui.button("Save", on_click=handle_create, color="primary").classes("q-mt-lg")
