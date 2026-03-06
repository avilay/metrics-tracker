from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class PropertyDef:
    name: str
    value_type: str  # 'numeric' or 'categorical'
    unit: str | None = None
    categories: list[str] = field(default_factory=list)


@dataclass
class MetricDefinition:
    id: int | None
    user_id: int
    name: str
    value_type: str  # 'numeric', 'categorical', 'none'
    unit: str | None = None
    categories: list[str] = field(default_factory=list)
    properties: list[PropertyDef] = field(default_factory=list)

    def to_definition_json(self) -> str:
        defn: dict = {"value_type": self.value_type}
        if self.unit:
            defn["unit"] = self.unit
        if self.categories:
            defn["categories"] = self.categories
        if self.properties:
            defn["properties"] = [
                {
                    "name": p.name,
                    "value_type": p.value_type,
                    **({"unit": p.unit} if p.unit else {}),
                    **({"categories": p.categories} if p.categories else {}),
                }
                for p in self.properties
            ]
        return json.dumps(defn)

    @classmethod
    def from_row(cls, row: dict) -> MetricDefinition:
        defn = json.loads(row["definition_json"])
        properties = [
            PropertyDef(
                name=p["name"],
                value_type=p["value_type"],
                unit=p.get("unit"),
                categories=p.get("categories", []),
            )
            for p in defn.get("properties", [])
        ]
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            value_type=defn["value_type"],
            unit=defn.get("unit"),
            categories=defn.get("categories", []),
            properties=properties,
        )


@dataclass
class LogEntry:
    id: int | None
    metric_id: int
    recorded_at: int  # unix timestamp (seconds)
    value: float | None = None
    label: str | None = None
    properties: dict | None = None  # {"event": "breakfast", "delta": "one-hour-after"}

    @classmethod
    def from_row(cls, row: dict) -> LogEntry:
        props = json.loads(row["properties_json"]) if row["properties_json"] else None
        return cls(
            id=row["id"],
            metric_id=row["metric_id"],
            recorded_at=row["recorded_at"],
            value=row["value"],
            label=row["label"],
            properties=props,
        )


@dataclass
class User:
    id: int | None
    firebase_uid: str
    display_name: str | None = None
    email: str | None = None
    photo_url: str | None = None
    is_anonymous: bool = True
    created_at: int = 0
