from dataclasses import dataclass


@dataclass
class Entry:
    identity: str
    topic: str
    message: str
    timestamp: str
    created_at: int
