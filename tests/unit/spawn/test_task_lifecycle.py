"""Test spawn task lifecycle: task creation, status transitions, output capture."""

from space.os.spawn import registry


def test_task_pending_to_running(in_memory_db):
    """Task transitions from pending → running with started_at timestamp."""
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="list repos")

    task = registry.get_task(task_id)
    assert task["status"] == "pending"
    assert task["started_at"] is None

    registry.update_task(task_id, status="running", started_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "running"
    assert task["started_at"] is not None


def test_task_running_to_completed(in_memory_db):
    """Task transitions from running → completed with output and duration."""
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="list repos")
    registry.update_task(task_id, status="running", started_at=True)

    output = "repo1\nrepo2\nrepo3"
    registry.update_task(task_id, status="completed", output=output, completed_at=True)

    task = registry.get_task(task_id)
    assert task["status"] == "completed"
    assert task["output"] == output
    assert task["completed_at"] is not None
    assert task["duration"] is not None
    assert task["duration"] >= 0


def test_task_running_to_failed(in_memory_db):
    """Task transitions from running → failed with stderr."""
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="invalid command")
    registry.update_task(task_id, status="running", started_at=True)

    stderr = "command not found"
    registry.update_task(task_id, status="failed", stderr=stderr, completed_at=True)

    task = registry.get_task(task_id)
    assert task["status"] == "failed"
    assert task["stderr"] == stderr
    assert task["output"] is None
    assert task["completed_at"] is not None


def test_task_pending_to_timeout(in_memory_db):
    """Task can timeout without starting."""
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="slow task")

    registry.update_task(task_id, status="timeout", completed_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "timeout"
    assert task["started_at"] is None
    assert task["completed_at"] is not None


def test_task_lifecycle_with_channel(in_memory_db):
    """Task tracks channel_id for bridge integration."""
    registry.ensure_agent("hailot")
    channel_id = "ch-spawn-test-123"
    task_id = registry.create_task(
        identity="hailot",
        input="list repos",
        channel_id=channel_id,
    )

    task = registry.get_task(task_id)
    assert task["channel_id"] == channel_id

    registry.update_task(task_id, status="running", started_at=True)
    registry.update_task(task_id, status="completed", output="done", completed_at=True)

    task = registry.get_task(task_id)
    assert task["channel_id"] == channel_id
    assert task["status"] == "completed"


def test_multiple_tasks_per_identity(in_memory_db):
    """Can track multiple concurrent tasks per agent."""
    registry.ensure_agent("hailot")

    t1 = registry.create_task(identity="hailot", input="task 1")
    t2 = registry.create_task(identity="hailot", input="task 2")
    t3 = registry.create_task(identity="hailot", input="task 3")

    registry.update_task(t1, status="running", started_at=True)
    registry.update_task(t2, status="running", started_at=True)

    hailot_tasks = registry.list_tasks(identity="hailot")
    assert len(hailot_tasks) == 3

    running = registry.list_tasks(status="running", identity="hailot")
    assert len(running) == 2
    assert {t["id"] for t in running} == {t1, t2}

    pending = registry.list_tasks(status="pending", identity="hailot")
    assert len(pending) == 1
    assert pending[0]["id"] == t3


def test_task_output_capture(in_memory_db):
    """Tasks capture both stdout and stderr."""
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="run with mixed output")

    registry.update_task(task_id, status="running", started_at=True)
    registry.update_task(
        task_id,
        status="completed",
        output="stdout content",
        stderr="stderr content",
        completed_at=True,
    )

    task = registry.get_task(task_id)
    assert task["output"] == "stdout content"
    assert task["stderr"] == "stderr content"
