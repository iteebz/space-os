from dataclasses import dataclass, field
from enum import Enum


class SpawnStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Agent:
    agent_id: str
    identity: str
    model: str
    constitution: str | None = None
    role: str | None = None
    spawn_count: int = 0
    created_at: str | None = None
    last_active_at: str | None = None
    archived_at: str | None = None

    @property
    def provider(self) -> str:
        model_lower = self.model.lower()
        if model_lower.startswith("gpt-"):
            return "codex"
        if model_lower.startswith("gemini"):
            return "gemini"
        if model_lower.startswith("claude"):
            return "claude"
        return "claude"


@dataclass
class Channel:
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
    message_id: str
    channel_id: str
    agent_id: str
    content: str
    created_at: str


@dataclass
class Spawn:
    id: str
    agent_id: str
    status: SpawnStatus | str = SpawnStatus.PENDING
    is_ephemeral: bool = False
    constitution_hash: str | None = None
    channel_id: str | None = None
    pid: int | None = None
    session_id: str | None = None
    created_at: str | None = None
    ended_at: str | None = None


@dataclass
class Memory:
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
    knowledge_id: str
    domain: str
    agent_id: str
    content: str
    created_at: str
    archived_at: str | None = None


@dataclass
class Task:
    task_id: str
    creator_id: str
    content: str
    project: str | None
    status: TaskStatus | str = TaskStatus.OPEN
    created_at: str | None = None
    agent_id: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


@dataclass
class Session:
    session_id: str
    provider: str
    model: str
    message_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_count: int = 0
    source_path: str | None = None
    first_message_at: str | None = None
    last_message_at: str | None = None


@dataclass
class SessionMessage:
    """Event from session JSONL: text, tool call, tool result, or message."""

    type: str
    timestamp: str | None
    content: dict | str | None = None


@dataclass
class AgentStats:
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
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    channels: int = 0
    active_channels: int = 0
    archived_channels: int = 0


@dataclass
class MemoryStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0


@dataclass
class KnowledgeStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0


@dataclass
class SpawnStats:
    available: bool
    total: int = 0
    agents: int = 0
    hashes: int = 0


@dataclass
class SessionStats:
    available: bool
    total_sessions: int = 0
    total_messages: int = 0
    total_tools_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    by_provider: dict[str, dict] | None = None
    by_agent: list[dict] | None = None


@dataclass
class SpaceStats:
    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats
    spawn: SpawnStats
    sessions: SessionStats | None = None
    agents: list[AgentStats] | None = None


@dataclass
class Export:
    channel_id: str
    channel_name: str
    topic: str | None
    created_at: str | None
    members: list[str]
    message_count: int
    messages: list[Message]


@dataclass
class Canon:
    path: str
    content: str
    created_at: str | None = None


@dataclass
class SearchResult:
    """Unified search result across all primitives."""

    source: str
    reference: str
    content: str
    timestamp: str
    agent_id: str | None = None
    identity: str | None = None
    metadata: dict | None = None
