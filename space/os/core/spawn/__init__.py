from . import api, db
from .api import (
    archive_agent,
    clear_cache,
    connect,
    create_task,
    ensure_agent,
    get_agent_id,
    get_agent_ids,
    get_agent_name,
    get_self_description,
    get_task,
    list_all_agents,
    list_tasks,
    merge_agents,
    rename_agent,
    restore_agent,
    set_self_description,
    update_task,
)
from .spawn import get_base_agent, inject_role, resolve_model_alias

db.register()

__all__ = [
    "api",
    "db",
    "get_base_agent",
    "inject_role",
    "resolve_model_alias",
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
    "connect",
]
