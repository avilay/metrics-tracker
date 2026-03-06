"""Unit tests for analysis.load_metrics using the pre-populated metrics-tracker.db."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import analysis
import pandas as pd
import pytest

# Patch the module-level connection before importing analysis
DB_PATH = Path(__file__).parent / "metrics-tracker.db"


def _query_db(sql, params=()):
    """Run a read-only query against the test database."""
    conn = sqlite3.connect(DB_PATH)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


@pytest.fixture()
def _load():
    """Helper that returns load_metrics bound to user_id=1."""

    def _inner(metric_name: str) -> pd.DataFrame:
        return analysis.load_metrics(user_id=1, metric_name=metric_name, tz="UTC")

    return _inner


# ── Meditation (value_type=none, no properties) ──────────────────────────


class TestMeditation:
    def test_row_count(self, _load):
        df = _load("Meditation")
        assert len(df) == 16

    def test_columns(self, _load):
        df = _load("Meditation")
        assert list(df.columns) == ["recorded_at"]

    def test_recorded_at_dtype(self, _load):
        df = _load("Meditation")
        assert df["recorded_at"].dtype == "datetime64[s, UTC]"

    def test_index_matches_log_ids(self, _load):
        df = _load("Meditation")
        ids = [
            r[0] for r in _query_db("SELECT id FROM logs WHERE metric_id=1 ORDER BY id")
        ]
        assert sorted(df.index.tolist()) == ids


# ── Weight (value_type=numeric, no properties) ───────────────────────────


class TestWeight:
    def test_row_count(self, _load):
        df = _load("Weight")
        assert len(df) == 28

    def test_columns(self, _load):
        df = _load("Weight")
        assert list(df.columns) == ["recorded_at", "value"]

    def test_value_dtype(self, _load):
        df = _load("Weight")
        assert df["value"].dtype == "float64"

    def test_values_match_db(self, _load):
        df = _load("Weight")
        rows = _query_db("SELECT id, value FROM logs WHERE metric_id=2 ORDER BY id")
        for log_id, expected_val in rows:
            assert df.loc[log_id, "value"] == pytest.approx(expected_val)

    def test_recorded_at_values(self, _load):
        """Spot-check that timestamps are correctly converted."""
        df = _load("Weight")
        row = _query_db(
            "SELECT id, recorded_at FROM logs WHERE metric_id=2 ORDER BY id LIMIT 1"
        )[0]
        expected = datetime.fromtimestamp(row[1], tz=timezone.utc)
        actual = df.loc[row[0], "recorded_at"].to_pydatetime()
        assert actual == expected


class TestMood:
    def test_row_count(self, _load):
        df = _load("Mood")
        assert len(df) == 63

    def test_columns(self, _load):
        df = _load("Mood")
        assert list(df.columns) == ["recorded_at", "value"]

    def test_value_is_categorical(self, _load):
        df = _load("Mood")
        assert isinstance(df["value"].dtype, pd.CategoricalDtype)

    def test_categories(self, _load):
        df = _load("Mood")
        assert list(df["value"].cat.categories) == ["happy", "sad", "serene", "angry"]

    def test_all_values_in_categories(self, _load):
        df = _load("Mood")
        assert df["value"].isna().sum() == 0


# ── Meal (value_type=none, with properties) ──────────────────────────────


class TestMeal:
    def test_row_count(self, _load):
        df = _load("Meal")
        assert len(df) == 84

    def test_columns(self, _load):
        df = _load("Meal")
        expected = [
            "recorded_at",
            "source",
            "taste",
            "is_filling",
            "healthy",
        ]
        assert list(df.columns) == expected

    def test_source_is_categorical(self, _load):
        df = _load("Meal")
        assert isinstance(df["source"].dtype, pd.CategoricalDtype)
        assert list(df["source"].cat.categories) == [
            "home-cooked",
            "take-out",
            "tiffin",
        ]

    def test_taste_is_categorical(self, _load):
        df = _load("Meal")
        assert isinstance(df["taste"].dtype, pd.CategoricalDtype)
        assert list(df["taste"].cat.categories) == ["delicious", "edible", "bad"]

    def test_is_filling_is_boolean(self, _load):
        df = _load("Meal")
        assert df["is_filling"].dtype == "boolean"

    def test_healthy_is_categorical(self, _load):
        df = _load("Meal")
        assert isinstance(df["healthy"].dtype, pd.CategoricalDtype)
        assert list(df["healthy"].cat.categories) == ["very", "medium", "no"]

    def test_property_values_match_db(self, _load):
        """Spot-check first row's properties against the database."""
        df = _load("Meal")
        first_id = int(df.index[0])  # cast from numpy int64 for sqlite3
        row = _query_db("SELECT properties_json FROM logs WHERE id=?", (first_id,))[0]
        props = json.loads(row[0])
        assert df.loc[first_id, "source"] == props["source"]
        assert df.loc[first_id, "taste"] == props["taste"]
        assert df.loc[first_id, "is_filling"] == props["is_filling"]
        assert df.loc[first_id, "healthy"] == props["healthy"]


# ── Blood Glucose (value_type=numeric, with properties) ──────────────────


class TestBloodGlucose:
    def test_row_count(self, _load):
        df = _load("Blood Glucose")
        assert len(df) == 51

    def test_columns(self, _load):
        df = _load("Blood Glucose")
        expected = ["recorded_at", "value", "event", "delta"]
        assert list(df.columns) == expected

    def test_value_dtype(self, _load):
        df = _load("Blood Glucose")
        assert df["value"].dtype == "float64"

    def test_event_is_categorical(self, _load):
        df = _load("Blood Glucose")
        assert isinstance(df["event"].dtype, pd.CategoricalDtype)
        assert list(df["event"].cat.categories) == [
            "fasting",
            "breakfast",
            "workout",
            "ad-hoc",
        ]

    def test_delta_is_categorical(self, _load):
        df = _load("Blood Glucose")
        assert isinstance(df["delta"].dtype, pd.CategoricalDtype)
        assert list(df["delta"].cat.categories) == [
            "one-hour-after",
            "two-hours-after",
        ]

    def test_fasting_has_null_delta(self, _load):
        """Fasting readings should have NaN delta (null in the JSON)."""
        df = _load("Blood Glucose")
        fasting = df[df["event"] == "fasting"]
        assert len(fasting) > 0
        assert fasting["delta"].isna().all()


# ── Hike (value_type=numeric, with mixed properties) ─────────────────────


class TestHike:
    def test_row_count(self, _load):
        df = _load("Hike")
        assert len(df) == 7

    def test_columns(self, _load):
        df = _load("Hike")
        expected = [
            "recorded_at",
            "value",
            "loop_length",
            "elevation_gain",
            "landscape",
        ]
        assert list(df.columns) == expected

    def test_numeric_property_dtypes(self, _load):
        df = _load("Hike")
        assert df["loop_length"].dtype == "float64"
        assert df["elevation_gain"].dtype == "float64"

    def test_landscape_is_categorical(self, _load):
        df = _load("Hike")
        assert isinstance(df["landscape"].dtype, pd.CategoricalDtype)
        assert list(df["landscape"].cat.categories) == [
            "coastal",
            "lake",
            "river",
            "mountain",
            "ridge",
            "woods",
        ]

    def test_values_match_db(self, _load):
        """Check all hike rows against the database."""
        df = _load("Hike")
        rows = _query_db(
            "SELECT id, value, properties_json FROM logs WHERE metric_id=6 ORDER BY id"
        )
        for log_id, value, props_json in rows:
            props = json.loads(props_json)
            assert df.loc[log_id, "value"] == pytest.approx(value)
            assert df.loc[log_id, "loop_length"] == pytest.approx(props["loop_length"])
            assert df.loc[log_id, "elevation_gain"] == pytest.approx(
                props["elevation_gain"]
            )
            assert df.loc[log_id, "landscape"] == props["landscape"]
