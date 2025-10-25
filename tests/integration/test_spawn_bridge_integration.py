"""Integration: bridge creates spawn tasks, not bridge.db tasks."""

from space.os.core import bridge, spawn


def test_bridge_uses_spawn_tasks(test_space):
    """When bridge spawns agent, task lives in spawn.db not bridge.db."""

    bridge.db.connect()

    spawn.db.ensure_agent("zealot")

    task_id = spawn.db.create_task(
        role="zealot",
        input="list repos",
        channel_id="ch-test-123",
    )

    task = spawn.db.get_task(task_id)
    assert spawn.db.get_agent_name(task.agent_id) == "zealot"
    assert task.channel_id == "ch-test-123"
    assert task.status == "pending"


def test_task_lifecycle_pending_to_completed(test_space):
    """Task moves through states: pending → running → completed."""

    spawn.db.ensure_agent("zealot")

    task_id = spawn.db.create_task(role="zealot", input="task")

    task = spawn.db.get_task(task_id)
    assert task.status == "pending"

    spawn.db.update_task(task_id, status="running", mark_started=True)
    task = spawn.db.get_task(task_id)
    assert task.status == "running"

    spawn.db.update_task(task_id, status="completed", output="done", mark_completed=True)
    task = spawn.db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == "done"
    assert task.duration is not None


def test_multiple_agents_concurrent_tasks(test_space):
    """Multiple agents can have concurrent tasks."""

    spawn.db.ensure_agent("zealot")
    spawn.db.ensure_agent("sentinel")

    z1 = spawn.db.create_task(role="zealot", input="zealot task 1")
    spawn.db.create_task(role="zealot", input="zealot task 2")
    s1 = spawn.db.create_task(role="sentinel", input="sentinel task 1")

    spawn.db.update_task(z1, status="running", mark_started=True)
    spawn.db.update_task(s1, status="running", mark_started=True)

    zealot_running = spawn.db.list_tasks(status="running", role="zealot")
    assert len(zealot_running) == 1
    assert zealot_running[0].task_id == z1

    zealot_tasks = spawn.db.list_tasks(role="zealot")
    assert len(zealot_tasks) == 1
    assert zealot_tasks[0].task_id == z1
