"""Daemon task API: create, schedule, manage autonomous swarms."""

from space.os.spawn.api import tasks, agents


def create_daemon_task(
    daemon_type: str,
    role: str = "zealot",
    channel_id: str | None = None,
) -> str:
    """Create a daemon task for a given type (upkeep, maintenance, etc).
    
    Args:
        daemon_type: Type of daemon task (upkeep, maintenance, verification, etc)
        role: Constitutional identity to run task (default: zealot)
        channel_id: Optional bridge channel for coordination
    
    Returns:
        task_id for tracking
    """
    agent = agents.get_agent(role)
    if not agent:
        raise ValueError(f"Agent '{role}' not found")
    
    task_input = f"Execute daemon task: {daemon_type}"
    task_id = tasks.create_task(
        identity=role,
        input=task_input,
        channel_id=channel_id,
    )
    return task_id


def get_daemon_task(task_id: str):
    """Get daemon task status."""
    return tasks.get_task(task_id)


def list_daemon_tasks(status: str | None = None):
    """List all daemon tasks, optionally filtered by status."""
    return tasks.list_tasks(status=status)
