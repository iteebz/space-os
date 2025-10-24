from dataclasses import dataclass


@dataclass
class Agent:
    agent_id: str
    name: str
    self_description: str | None = None
    archived_at: int | None = None
    created_at: str | None = None


@dataclass
class Task:
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
