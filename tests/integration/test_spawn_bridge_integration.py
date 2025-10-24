"""Integration: bridge creates spawn tasks, not bridge.db tasks."""

from space.os.core import bridge, spawn


def test_bridge_uses_spawn_tasks(test_space):
    """When bridge spawns agent, task lives in spawn.db not bridge.db."""

    bridge.db.connect()

    spawn.db.ensure_agent("hailot")

    task_id = spawn.db.create_task(
        identity="hailot",
        input="list repos",
        channel_id="ch-test-123",
    )

    task = spawn.db.get_task(task_id)
    assert spawn.db.get_agent_name(task.agent_id) == "hailot"
    assert task.channel_id == "ch-test-123"
    assert task.status == "pending"


def test_task_lifecycle_pending_to_completed(test_space):
    """Task moves through states: pending → running → completed."""

    spawn.db.ensure_agent("hailot")

    task_id = spawn.db.create_task(identity="hailot", input="task")

    task = spawn.db.get_task(task_id)
    assert task.status == "pending"

    spawn.db.update_task(task_id, status="running", started_at=True)
    task = spawn.db.get_task(task_id)
    assert task.status == "running"

    spawn.db.update_task(task_id, status="completed", output="done", completed_at=True)
    task = spawn.db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == "done"
    assert task.duration is not None


def test_multiple_agents_concurrent_tasks(test_space):
    """Multiple agents can have concurrent tasks."""

    spawn.db.ensure_agent("hailot")
    spawn.db.ensure_agent("zealot")

    h1 = spawn.db.create_task(identity="hailot", input="hailot task 1")
    spawn.db.create_task(identity="hailot", input="hailot task 2")
    z1 = spawn.db.create_task(identity="zealot", input="zealot task 1")

    spawn.db.update_task(h1, status="running", started_at=True)
    spawn.db.update_task(z1, status="running", started_at=True)

    hailot_running = spawn.db.list_tasks(status="running", identity="hailot")
    assert len(hailot_running) == 1
    assert hailot_running[0].task_id == h1

    zealot_tasks = spawn.db.list_tasks(identity="zealot")
    assert len(zealot_tasks) == 1
    assert zealot_tasks[0].task_id == z1
