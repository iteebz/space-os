from dataclasses import dataclass


@dataclass
class Entry:
    id: int
    agent_id: str
    role: str
    channels: list[str]
    registered_at: str
    constitution_hash: str
    self_description: str | None = None
    provider: str | None = None
    model: str | None = None
    identity: str | None = None  # Populated from join
