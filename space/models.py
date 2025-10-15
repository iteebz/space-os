"""Shared data models and types."""

from dataclasses import dataclass


@dataclass
class Message:
    """A coordination message."""

    message_id: str
    channel_id: str
    agent_id: str
    content: str
    created_at: str


@dataclass
class Channel:
    """A coordination channel."""

    channel_id: str
    name: str
    topic: str | None = None
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
class Note:
    """A note associated with a channel."""

    note_id: str
    agent_id: str
    content: str
    created_at: str


@dataclass
class Export:
    """Complete channel export for research."""

    channel_id: str
    channel_name: str
    topic: str | None
    created_at: str | None
    participants: list[str]
    message_count: int
    messages: list[Message]
    notes: list[Note]


@dataclass
class Memory:
    memory_id: str
    agent_id: str
    topic: str
    message: str
    timestamp: str
    created_at: int
    archived_at: int | None = None
    core: bool = False
    source: str = "manual"
    bridge_channel: str | None = None
    code_anchors: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    synthesis_note: str | None = None


@dataclass
class Event:
    """An event for provenance tracking."""

    event_id: str
    timestamp: str
    type: str
    source: str
    data: dict | None = None


@dataclass
class Knowledge:
    """A knowledge artifact."""

    knowledge_id: str
    domain: str
    agent_id: str
    content: str
    confidence: float | None
    created_at: str
    archived_at: int | None = None
