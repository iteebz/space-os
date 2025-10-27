from . import api, db
from .api import (
    archive_agent,
    clone_agent,
    complete_task,
    create_task,
    describe_self,
    ensure_agent,
    fail_task,
    get_agent,
    get_task,
    launch_agent,
    list_agents,
    list_tasks,
    merge_agents,
    register_agent,
    rename_agent,
    start_task,
    unarchive_agent,
    update_agent,
)
from .commands import app
from .spawn import resolve_model_alias

db.register()

__all__ = [
    "api",
    "db",
    "app",
    "resolve_model_alias",
    "get_agent",
    "register_agent",
    "update_agent",
    "clone_agent",
    "ensure_agent",
    "describe_self",
    "rename_agent",
    "archive_agent",
    "unarchive_agent",
    "list_agents",
    "merge_agents",
    "launch_agent",
    "create_task",
    "get_task",
    "list_tasks",
    "start_task",
    "complete_task",
    "fail_task",
]
