"""Integration: bridge creates spawn tasks, not bridge.db tasks."""

from space.os.bridge import db as bridge_db
from space.os.spawn import db as spawn_db


def test_bridge_uses_spawn_tasks(test_space):
    """When bridge spawns agent, task lives in spawn.db not bridge.db."""

    bridge_db.connect()

    spawn_db.ensure_agent("hailot")

    task_id = spawn_db.create_task(
        identity="hailot",
        input="list repos",
        channel_id="ch-test-123",
    )

    task = spawn_db.get_task(task_id)
    assert spawn_db.get_identity(task.agent_id) == "hailot"
    assert task.channel_id == "ch-test-123"
    assert task.status == "pending"


def test_task_lifecycle_pending_to_completed(test_space):
    """Task moves through states: pending → running → completed."""

    spawn_db.ensure_agent("hailot")

    task_id = spawn_db.create_task(identity="hailot", input="task")

    task = spawn_db.get_task(task_id)
    assert task.status == "pending"

    spawn_db.update_task(task_id, status="running", started_at=True)
    task = spawn_db.get_task(task_id)
    assert task.status == "running"

    spawn_db.update_task(task_id, status="completed", output="done", completed_at=True)
    task = spawn_db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == "done"
    assert task.duration is not None


def test_multiple_agents_concurrent_tasks(test_space):
    """Multiple agents can have concurrent tasks."""

    spawn_db.ensure_agent("hailot")
    spawn_db.ensure_agent("zealot")

    h1 = spawn_db.create_task(identity="hailot", input="hailot task 1")
    spawn_db.create_task(identity="hailot", input="hailot task 2")
    z1 = spawn_db.create_task(identity="zealot", input="zealot task 1")

    spawn_db.update_task(h1, status="running", started_at=True)
    spawn_db.update_task(z1, status="running", started_at=True)

    hailot_running = spawn_db.list_tasks(status="running", identity="hailot")
    assert len(hailot_running) == 1
    assert hailot_running[0].task_id == h1

    zealot_tasks = spawn_db.list_tasks(identity="zealot")
    assert len(zealot_tasks) == 1
    assert zealot_tasks[0].task_id == z1
