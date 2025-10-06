"""Bridge data models and types."""

from dataclasses import dataclass


@dataclass
class Message:
    """A coordination message."""

    id: int
    channel_id: str
    sender: str
    content: str
    created_at: str


@dataclass
class Channel:
    """A coordination channel."""

    name: str
    context: str | None = None
    created_at: str | None = None
    archived_at: str | None = None
    participants: list[str] = None
    message_count: int = 0
    last_activity: str | None = None
    unread_count: int = 0
    notes_count: int = 0

    def __post_init__(self):
        if self.participants is None:
            self.participants = []


@dataclass
class Bookmark:
    """Agent's bookmark for a channel."""

    agent_id: str
    channel_id: str
    last_seen_id: int = 0


@dataclass
class ExportData:
    """Complete channel export for research."""

    channel_id: str
    channel_name: str
    context: str | None
    created_at: str | None
    participants: list[str]
    message_count: int
    messages: list[dict]
    notes: list[dict]
