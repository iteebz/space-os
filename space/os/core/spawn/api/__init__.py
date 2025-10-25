from pathlib import Path

from space.os.lib import db, paths

from . import agents, tasks
from .agents import (
    archive_agent,
    clear_cache,
    ensure_agent,
    get_agent_id,
    get_agent_ids,
    get_agent_name,
    get_self_description,
    list_all_agents,
    merge_agents,
    rename_agent,
    restore_agent,
    set_self_description,
)
from .tasks import create_task, get_task, list_tasks, update_task

__all__ = [
    "agents",
    "tasks",
    "get_agent_ids",
    "get_agent_id",
    "get_agent_name",
    "clear_cache",
    "ensure_agent",
    "get_self_description",
    "set_self_description",
    "rename_agent",
    "archive_agent",
    "restore_agent",
    "list_all_agents",
    "merge_agents",
    "create_task",
    "get_task",
    "update_task",
    "list_tasks",
    "path",
    "connect",
]


def path() -> Path:
    return paths.space_data() / "spawn.db"


def connect():
    """Return connection to spawn database via central registry."""
    return db.ensure("spawn")
