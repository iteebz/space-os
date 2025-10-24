"""Shared data models and types."""

from dataclasses import dataclass, field


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
    participants: list[str] = field(default_factory=list)
    message_count: int = 0
    last_activity: str | None = None
    unread_count: int = 0
    notes_count: int = 0


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
    synthesis_note: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None


@dataclass
class Event:
    """An event for provenance tracking."""

    event_id: str
    source: str
    agent_id: str | None
    event_type: str
    data: str | None = None
    timestamp: int | None = None
    chat_id: str | None = None


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


@dataclass
class Agent:
    """An agent in the spawn registry."""

    agent_id: str
    name: str
    self_description: str | None = None
    archived_at: int | None = None
    created_at: str | None = None


@dataclass
class Task:
    """A task spawned by an agent."""

    task_id: str
    agent_id: str
    input: str
    status: str = "pending"
    channel_id: str | None = None
    output: str | None = None
    stderr: str | None = None
    pid: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str | None = None
    duration: float | None = None
