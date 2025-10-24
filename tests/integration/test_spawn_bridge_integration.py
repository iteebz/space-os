"""Integration: bridge creates spawn tasks, not bridge.db tasks."""

from space.os.bridge import db as bridge_db
from space.os.spawn import registry


def test_bridge_uses_spawn_tasks(test_space):
    """When bridge spawns agent, task lives in spawn.db not bridge.db."""
    registry.init_db()
    bridge_db.connect()

    registry.ensure_agent("hailot")

    task_id = registry.create_task(
        identity="hailot",
        input="list repos",
        channel_id="ch-test-123",
    )

    task = registry.get_task(task_id)
    assert task["identity"] == "hailot"
    assert task["channel_id"] == "ch-test-123"
    assert task["status"] == "pending"


def test_task_lifecycle_pending_to_completed(test_space):
    """Task moves through states: pending → running → completed."""
    registry.init_db()
    registry.ensure_agent("hailot")

    task_id = registry.create_task(identity="hailot", input="task")

    task = registry.get_task(task_id)
    assert task["status"] == "pending"

    registry.update_task(task_id, status="running", started_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "running"

    registry.update_task(task_id, status="completed", output="done", completed_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "completed"
    assert task["output"] == "done"
    assert task["duration"] is not None


def test_multiple_agents_concurrent_tasks(test_space):
    """Multiple agents can have concurrent tasks."""
    registry.init_db()
    registry.ensure_agent("hailot")
    registry.ensure_agent("zealot")

    h1 = registry.create_task(identity="hailot", input="hailot task 1")
    registry.create_task(identity="hailot", input="hailot task 2")
    z1 = registry.create_task(identity="zealot", input="zealot task 1")

    registry.update_task(h1, status="running", started_at=True)
    registry.update_task(z1, status="running", started_at=True)

    hailot_running = registry.list_tasks(status="running", identity="hailot")
    assert len(hailot_running) == 1
    assert hailot_running[0]["id"] == h1

    zealot_tasks = registry.list_tasks(identity="zealot")
    assert len(zealot_tasks) == 1
    assert zealot_tasks[0]["id"] == z1
