"""High-level API for ops primitive."""

from space.ops import db


def create(
    description: str,
    parent_id: str | None = None,
    channel_id: str | None = None,
    assigned_to: str | None = None,
) -> str:
    """Create a task."""
    return db.create_task(description, parent_id, channel_id, assigned_to)


def get(task_id: str):
    """Get a task by ID."""
    return db.get_task(task_id)


def list_tasks(
    status: str | None = None,
    assigned_to: str | None = None,
    parent_id: str | None = None,
):
    """List tasks with filters."""
    return db.list_tasks(status, assigned_to, parent_id)


def claim(task_id: str, agent_id: str) -> bool:
    """Claim a task for an agent."""
    return db.claim_task(task_id, agent_id)


def complete(task_id: str, handover: str, agent_id: str) -> bool:
    """Complete a task with handover."""
    return db.complete_task(task_id, handover, agent_id)


def block(task_id: str, reason: str) -> bool:
    """Block a task."""
    return db.block_task(task_id, reason)


def tree(task_id: str) -> dict:
    """Get task tree structure."""
    return db.get_task_tree(task_id)


def reduce(parent_id: str, handover: str, agent_id: str) -> bool:
    """Reduce subtasks into parent task completion.

    Aggregates completed subtasks and marks parent as complete.
    """
    parent = db.get_task(parent_id)
    if not parent:
        return False

    subtasks = db.get_subtasks(parent_id)
    if not subtasks:
        return False

    # Check if all subtasks are complete
    incomplete = [st for st in subtasks if st.status != "complete"]
    if incomplete:
        return False

    # Claim parent if not already assigned
    if not parent.assigned_to:
        db.claim_task(parent_id, agent_id)

    # Aggregate subtask handovers
    aggregated = "\n\n".join(
        [f"**{st.description}**\n{st.handover or '(no handover)'}" for st in subtasks]
    )
    final_handover = f"{handover}\n\n## Subtask Results\n\n{aggregated}"

    # Mark parent complete
    return db.complete_task(parent_id, final_handover, agent_id)
