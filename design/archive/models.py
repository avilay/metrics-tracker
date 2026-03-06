from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Property:
    id: int
    name: str
    value: float | str


@dataclass
class Log:
    id: int
    recorded_at: datetime
    value: float | str | None = None
    properties: list[Property] = field(default_factory=list)


@dataclass
class Metric:
    id: int
    name: str
    logs: list[Log] = field(default_factory=list)
