from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Event:
    id: str
    timestamp: int
    source: str
    event_type: str
    identity: str | None = None
    data: dict[str, Any] | None = None
