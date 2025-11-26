from pathlib import Path

from space.core.models import Agent, Spawn
from space.lib import paths

PROVIDER_MAP = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "codex": "AGENTS.md",
}


def constitute(spawn: Spawn, agent: Agent) -> Path:
    target_dir = paths.identity_dir(agent.identity)
    target_dir.mkdir(parents=True, exist_ok=True)

    if agent.constitution:
        const_path = paths.constitution(agent.constitution)
        constitution_content = const_path.read_text()
        (target_dir / PROVIDER_MAP[agent.provider]).write_text(constitution_content)

    return target_dir


__all__ = [
    "constitute",
    "PROVIDER_MAP",
]
