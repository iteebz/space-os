"""Task primitive: shared work ledger for multi-agent swarms."""

from .cli import app, main
from .operations import add_task, done_task, get_task, list_tasks, remove_claim, start_task

__all__ = [
    "add_task",
    "app",
    "done_task",
    "get_task",
    "list_tasks",
    "main",
    "remove_claim",
    "start_task",
]
