import json
import time
from pathlib import Path

import pytest

from app.database import get_connection, init_db
from app.models import LogEntry, MetricDefinition, PropertyDef
from app.repositories.metric_repo import (
    create_metric,
    delete_metric,
    get_logs_for_metric,
    get_metric_by_id,
    get_metrics_for_user,
    insert_log,
)
from app.repositories.user_repo import get_user_by_firebase_uid, upsert_user


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    conn = get_connection(db_path)
    yield conn
    conn.close()


class TestSchema:
    def test_tables_exist(self, db):
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [r["name"] for r in tables]
        assert "users" in names
        assert "metrics" in names
        assert "logs" in names

    def test_value_type_constraint(self, db):
        with pytest.raises(Exception):
            db.execute(
                "INSERT INTO metrics (user_id, name, value_type, definition_json) VALUES (1, 'bad', 'invalid', '{}')"
            )

    def test_foreign_keys_enforced(self, db):
        with pytest.raises(Exception):
            db.execute(
                "INSERT INTO logs (metric_id, recorded_at) VALUES (9999, 100)"
            )
            db.commit()


class TestUserRepo:
    def test_create_anonymous_user(self, db):
        user = upsert_user(db, "uid-123", is_anonymous=True)
        assert user.id is not None
        assert user.firebase_uid == "uid-123"
        assert user.is_anonymous is True

    def test_upsert_upgrades_to_google(self, db):
        user1 = upsert_user(db, "uid-456", is_anonymous=True)
        user2 = upsert_user(db, "uid-456", is_anonymous=False, display_name="Alice", email="alice@example.com")
        assert user2.id == user1.id
        assert user2.is_anonymous is False
        assert user2.display_name == "Alice"

    def test_get_user_by_firebase_uid(self, db):
        upsert_user(db, "uid-789", is_anonymous=True)
        user = get_user_by_firebase_uid(db, "uid-789")
        assert user is not None
        assert user.firebase_uid == "uid-789"

    def test_get_nonexistent_user(self, db):
        assert get_user_by_firebase_uid(db, "no-such-uid") is None


class TestMetricRepo:
    def _create_user(self, db):
        return upsert_user(db, f"uid-{time.time_ns()}", is_anonymous=True)

    def test_create_and_get_numeric_metric(self, db):
        user = self._create_user(db)
        metric = MetricDefinition(
            id=None, user_id=user.id, name="Weight", value_type="numeric", unit="lbs"
        )
        created = create_metric(db, metric)
        assert created.id is not None

        fetched = get_metric_by_id(db, created.id)
        assert fetched.name == "Weight"
        assert fetched.value_type == "numeric"
        assert fetched.unit == "lbs"

    def test_create_categorical_metric(self, db):
        user = self._create_user(db)
        metric = MetricDefinition(
            id=None, user_id=user.id, name="Mood", value_type="categorical",
            categories=["happy", "sad", "angry", "serene"]
        )
        created = create_metric(db, metric)
        fetched = get_metric_by_id(db, created.id)
        assert fetched.value_type == "categorical"
        assert fetched.categories == ["happy", "sad", "angry", "serene"]

    def test_create_none_metric(self, db):
        user = self._create_user(db)
        metric = MetricDefinition(
            id=None, user_id=user.id, name="Meditate", value_type="none"
        )
        created = create_metric(db, metric)
        fetched = get_metric_by_id(db, created.id)
        assert fetched.value_type == "none"

    def test_metric_with_properties(self, db):
        user = self._create_user(db)
        metric = MetricDefinition(
            id=None, user_id=user.id, name="Blood Glucose", value_type="numeric", unit="mg/dL",
            properties=[
                PropertyDef(name="event", value_type="categorical", categories=["fasting", "breakfast", "workout"]),
                PropertyDef(name="delta", value_type="categorical", categories=["one-hour-after", "two-hours-after"]),
            ]
        )
        created = create_metric(db, metric)
        fetched = get_metric_by_id(db, created.id)
        assert len(fetched.properties) == 2
        assert fetched.properties[0].name == "event"
        assert fetched.properties[0].categories == ["fasting", "breakfast", "workout"]

    def test_metric_with_mixed_properties(self, db):
        user = self._create_user(db)
        metric = MetricDefinition(
            id=None, user_id=user.id, name="Hike", value_type="numeric", unit="minutes",
            properties=[
                PropertyDef(name="loop_length", value_type="numeric", unit="miles"),
                PropertyDef(name="elevation_gain", value_type="numeric", unit="feet"),
                PropertyDef(name="landscape", value_type="categorical", categories=["coastal", "mountain", "woods"]),
            ]
        )
        created = create_metric(db, metric)
        fetched = get_metric_by_id(db, created.id)
        assert len(fetched.properties) == 3
        assert fetched.properties[0].value_type == "numeric"
        assert fetched.properties[0].unit == "miles"
        assert fetched.properties[2].value_type == "categorical"

    def test_get_metrics_for_user(self, db):
        user = self._create_user(db)
        create_metric(db, MetricDefinition(id=None, user_id=user.id, name="A", value_type="none"))
        create_metric(db, MetricDefinition(id=None, user_id=user.id, name="B", value_type="none"))
        metrics = get_metrics_for_user(db, user.id)
        assert len(metrics) == 2

    def test_delete_metric(self, db):
        user = self._create_user(db)
        m = create_metric(db, MetricDefinition(id=None, user_id=user.id, name="X", value_type="none"))
        insert_log(db, LogEntry(id=None, metric_id=m.id, recorded_at=int(time.time())))
        delete_metric(db, m.id)
        assert get_metric_by_id(db, m.id) is None
        assert get_logs_for_metric(db, m.id) == []


class TestLogRepo:
    def _setup(self, db):
        user = upsert_user(db, f"uid-{time.time_ns()}", is_anonymous=True)
        metric = create_metric(db, MetricDefinition(
            id=None, user_id=user.id, name="Weight", value_type="numeric", unit="lbs"
        ))
        return user, metric

    def test_insert_numeric_log(self, db):
        _, metric = self._setup(db)
        entry = insert_log(db, LogEntry(
            id=None, metric_id=metric.id, recorded_at=1700000000, value=182.5
        ))
        assert entry.id is not None

        logs = get_logs_for_metric(db, metric.id)
        assert len(logs) == 1
        assert logs[0].value == 182.5

    def test_insert_categorical_log(self, db):
        user = upsert_user(db, f"uid-{time.time_ns()}", is_anonymous=True)
        metric = create_metric(db, MetricDefinition(
            id=None, user_id=user.id, name="Mood", value_type="categorical",
            categories=["happy", "sad"]
        ))
        insert_log(db, LogEntry(
            id=None, metric_id=metric.id, recorded_at=1700000000, label="happy"
        ))
        logs = get_logs_for_metric(db, metric.id)
        assert logs[0].label == "happy"

    def test_insert_log_with_properties(self, db):
        user = upsert_user(db, f"uid-{time.time_ns()}", is_anonymous=True)
        metric = create_metric(db, MetricDefinition(
            id=None, user_id=user.id, name="Glucose", value_type="numeric", unit="mg/dL",
            properties=[
                PropertyDef(name="event", value_type="categorical", categories=["fasting", "breakfast"]),
            ]
        ))
        insert_log(db, LogEntry(
            id=None, metric_id=metric.id, recorded_at=1700000000, value=105.0,
            properties={"event": "fasting"}
        ))
        logs = get_logs_for_metric(db, metric.id)
        assert logs[0].properties == {"event": "fasting"}
        assert logs[0].value == 105.0

    def test_insert_none_log(self, db):
        user = upsert_user(db, f"uid-{time.time_ns()}", is_anonymous=True)
        metric = create_metric(db, MetricDefinition(
            id=None, user_id=user.id, name="Meditate", value_type="none"
        ))
        insert_log(db, LogEntry(
            id=None, metric_id=metric.id, recorded_at=1700000000
        ))
        logs = get_logs_for_metric(db, metric.id)
        assert logs[0].value is None
        assert logs[0].label is None

    def test_logs_ordered_by_recorded_at(self, db):
        _, metric = self._setup(db)
        insert_log(db, LogEntry(id=None, metric_id=metric.id, recorded_at=300, value=3.0))
        insert_log(db, LogEntry(id=None, metric_id=metric.id, recorded_at=100, value=1.0))
        insert_log(db, LogEntry(id=None, metric_id=metric.id, recorded_at=200, value=2.0))
        logs = get_logs_for_metric(db, metric.id)
        assert [l.recorded_at for l in logs] == [100, 200, 300]
