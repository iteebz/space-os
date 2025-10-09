from dataclasses import dataclass


@dataclass
class Entry:
    uuid: str
    identity: str
    topic: str
    message: str
    timestamp: str
    created_at: int
    archived_at: int | None = None
