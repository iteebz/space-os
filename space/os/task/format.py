"""Task formatting for CLI display."""

from space.core.models import Task
from space.os import spawn


def format_task_list(tasks: list[Task], show_creator: bool = False) -> str:
    """Format list of tasks for display.

    Returns one line per task with status, agent, and content.
    """
    if not tasks:
        return "No tasks"

    lines = []
    for task in tasks:
        agent_str = f" @{spawn.get_agent(task.agent_id).identity}" if task.agent_id else ""
        status_str = f"({task.status})" if task.status != "open" else ""
        project_str = f" [{task.project}]" if task.project else ""

        line = f"[{task.task_id[-8:]}] {task.content}{agent_str}{status_str}{project_str}"
        lines.append(line)

    return "\n".join(lines)


def format_task_detail(task: Task) -> str:
    """Format full task details."""
    agent = spawn.get_agent(task.agent_id) if task.agent_id else None
    creator = spawn.get_agent(task.creator_id)

    lines = [
        f"ID: {task.task_id}",
        f"Status: {task.status}",
        f"Created by: {creator.identity if creator else task.creator_id[:8]}",
        f"Created: {task.created_at}",
    ]

    if task.project:
        lines.append(f"Project: {task.project}")

    if agent:
        lines.append(f"Claimed by: {agent.identity}")

    if task.started_at:
        lines.append(f"Started: {task.started_at}")

    if task.completed_at:
        lines.append(f"Completed: {task.completed_at}")

    lines.append(f"\n{task.content}")

    return "\n".join(lines)
