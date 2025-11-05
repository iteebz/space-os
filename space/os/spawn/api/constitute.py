from pathlib import Path

from space.core.models import Agent, Spawn
from space.lib import paths

PROVIDER_MAP = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "codex": "AGENTS.md",
}


def constitute(spawn: Spawn, agent: Agent) -> Path:
    if not agent.constitution:
        target_dir = (
            paths.identity_dir(agent.identity) if spawn.is_ephemeral else paths.space_root()
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    const_path = paths.constitution(agent.constitution)
    constitution_content = const_path.read_text()

    target_dir = paths.identity_dir(agent.identity) if spawn.is_ephemeral else paths.space_root()
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / PROVIDER_MAP[agent.provider]).write_text(constitution_content)

    return target_dir


__all__ = [
    "constitute",
    "PROVIDER_MAP",
]
