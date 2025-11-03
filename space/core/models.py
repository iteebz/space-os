"""Shared data models and types."""

from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    """Valid task statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Agent:
    """An agent in the spawn registry."""

    agent_id: str
    identity: str
    model: str
    constitution: str | None = None
    role: str | None = None
    spawn_count: int = 0
    archived_at: str | None = None
    created_at: str | None = None
    last_active_at: str | None = None

    @property
    def provider(self) -> str:
        """Infer provider from model string."""
        model_lower = self.model.lower()
        if model_lower.startswith("gpt-"):
            return "codex"
        if model_lower.startswith("gemini-"):
            return "gemini"
        if model_lower.startswith("claude-"):
            return "claude"
        raise ValueError(f"Unknown provider for model: {self.model}")


@dataclass
class Channel:
    """A coordination channel."""

    channel_id: str
    name: str
    topic: str | None = None
    created_at: str | None = None
    archived_at: str | None = None
    pinned_at: str | None = None
    members: list[str] = field(default_factory=list)
    message_count: int = 0
    last_activity: str | None = None
    unread_count: int = 0


@dataclass
class Message:
    """A coordination message in the bridge."""

    message_id: str
    channel_id: str
    agent_id: str
    content: str
    created_at: str


@dataclass
class Bookmark:
    """Agent's bookmark for a channel."""

    agent_id: str
    channel_id: str
    session_id: str | None = None
    last_seen_id: str | None = None


@dataclass
class Session:
    """A session: single spawn invocation of an agent."""

    id: str
    agent_id: str
    status: TaskStatus | str = TaskStatus.PENDING
    is_task: bool = True
    constitution_hash: str | None = None
    channel_id: str | None = None
    pid: int | None = None
    created_at: str | None = None
    ended_at: str | None = None


Task = Session


@dataclass
class Chat:
    """A chat session tracked for audit trail."""

    id: str
    model: str
    provider: str
    file_path: str
    message_count: int = 0
    tools_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    first_message_at: str | None = None
    last_message_at: str | None = None
    session_id: str | None = None
    created_at: str | None = None


@dataclass
class Memory:
    """Agent memory: facts, journal, or extracted insights."""

    memory_id: str
    agent_id: str
    message: str
    topic: str
    created_at: str
    archived_at: str | None = None
    core: bool = False
    source: str = "manual"


@dataclass
class Knowledge:
    """A knowledge artifact."""

    knowledge_id: str
    domain: str
    agent_id: str
    content: str
    created_at: str
    archived_at: str | None = None


@dataclass
class Export:
    """Complete channel export for research."""

    channel_id: str
    channel_name: str
    topic: str | None
    created_at: str | None
    members: list[str]
    message_count: int
    messages: list[Message]


@dataclass
class ChatMessage:
    """A message from CLI chat history (distinct from bridge Message)."""

    id: int
    cli: str
    model: str | None
    session_id: str
    timestamp: str
    identity: str | None
    role: str
    text: str


@dataclass
class Canon:
    """A canon markdown document (read-only, git-backed)."""

    path: str
    content: str
    created_at: str | None = None


@dataclass
class AgentStats:
    """Statistics for a single agent."""

    agent_id: str
    identity: str
    events: int
    spawns: int
    msgs: int
    mems: int
    knowledge: int
    channels: list[str]
    last_active: str | None
    last_active_human: str | None = None


@dataclass
class BridgeStats:
    """Bridge communication statistics."""

    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    channels: int = 0
    active_channels: int = 0
    archived_channels: int = 0


@dataclass
class MemoryStats:
    """Agent memory statistics."""

    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0


@dataclass
class KnowledgeStats:
    """Shared knowledge statistics."""

    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0


@dataclass
class SpawnStats:
    """Agent spawn statistics."""

    available: bool
    total: int = 0
    agents: int = 0
    hashes: int = 0


@dataclass
class ChatStats:
    """Chat session statistics."""

    available: bool
    total_chats: int = 0
    total_messages: int = 0
    total_tools_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    by_provider: dict[str, dict] | None = None
    by_agent: list[dict] | None = None


@dataclass
class SpaceStats:
    """Unified space statistics across all primitives."""

    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats
    spawn: SpawnStats
    chats: ChatStats | None = None
    agents: list[AgentStats] | None = None
