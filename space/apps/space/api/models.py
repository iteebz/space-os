from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    identity: str
    count: int


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
    message_leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class MemoryStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class KnowledgeStats:
    available: bool
    total: int = 0
    active: int = 0
    archived: int = 0
    topics: int = 0
    leaderboard: list[LeaderboardEntry] | None = None


@dataclass
class SpawnStats:
    available: bool
    total: int = 0
    agents: int = 0
    hashes: int = 0


@dataclass
class ChatStats:
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
    bridge: BridgeStats
    memory: MemoryStats
    knowledge: KnowledgeStats
    spawn: SpawnStats
    chats: ChatStats | None = None
    agents: list[AgentStats] | None = None
