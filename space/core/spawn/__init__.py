from . import api, db
from .api import (
    archive_agent,
    complete_task,
    create_task,
    describe_self,
    ensure_agent,
    fail_task,
    get_agent,
    get_task,
    list_agents,
    list_tasks,
    merge_agents,
    register_agent,
    rename_agent,
    start_task,
    unarchive_agent,
)
from .commands import app
from .spawn import get_base_agent, build_identity_prompt, resolve_model_alias

db.register()

__all__ = [
    "api",
    "db",
    "app",
    "get_base_agent",
    "build_identity_prompt",
    "resolve_model_alias",
    "get_agent",
    "register_agent",
    "ensure_agent",
    "describe_self",
    "rename_agent",
    "archive_agent",
    "unarchive_agent",
    "list_agents",
    "merge_agents",
    "create_task",
    "get_task",
    "list_tasks",
    "start_task",
    "complete_task",
    "fail_task",
]
