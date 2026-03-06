meal_defn = {
    "name": "Meal",
    "value_type": "none",
    "properties": [
        {
            "name": "source",
            "value_type": "categorical",
            "categories": ["home-cooked", "take-out", "tiffin"],
        },
        {
            "name": "taste",
            "value_type": "categorical",
            "categories": ["delicious", "edible", "bad"],
        },
        {"name": "is_filling", "value_type": "boolean"},
        {
            "name": "healthy",
            "value_type": "categorical",
            "categories": ["very", "medium", "no"],
        },
    ],
}

glucose_defn = {
    "name": "Blood Glucose",
    "value_type": "numeric",
    "unit": "mg/dL",
    "properties": [
        {
            "name": "event",
            "value_type": "categorical",
            "categories": ["fasting", "breakfast", "workout", "ad-hoc"],
        },
        {
            "name": "delta",
            "value_type": "categorical",
            "categories": ["one-hour-after", "two-hours-after"],
        },
    ],
}

hike_defn = {
    "name": "Hike",
    "value_type": "numeric",
    "unit": "minutes",
    "properties": [
        {"name": "loop_length", "value_type": "numeric", "unit": "miles"},
        {"name": "elevation_gain", "value_type": "numeric", "unit": "feet"},
        {
            "name": "landscape",
            "value_type": "categorical",
            "categories": [
                "coastal",
                "lake",
                "river",
                "mountain",
                "ridge",
                "woods",
            ],
        },
    ],
}

mood_defn = {
    "name": "Mood",
    "value_type": "categorical",
    "categories": ["happy", "sad", "serene", "angry"],
}

weight_defn = {
    "name": "Weight",
    "value_type": "numeric",
    "unit": "lbs",
}

meditation_defn = {
    "name": "Meditation",
    "value_type": "none",
}
