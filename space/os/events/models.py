from dataclasses import dataclass


@dataclass
class Event:
    uuid: str
    source: str
    identity: str | None
    event_type: str
    data: str | None
    created_at: int
