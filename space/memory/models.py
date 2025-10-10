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
    core: bool = False
    source: str = "manual"
    bridge_channel: str | None = None
    code_anchors: str | None = None
