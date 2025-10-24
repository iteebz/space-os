"""Test spawn task lifecycle: task creation, status transitions, output capture."""

from space.os.core.spawn import db as spawn_db


def test_task_pending_to_running(test_space):
    """Task transitions from pending → running with started_at timestamp."""
    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="list repos")

    task = spawn_db.get_task(task_id)
    assert task.status == "pending"
    assert task.started_at is None

    spawn_db.update_task(task_id, status="running", started_at=True)
    task = spawn_db.get_task(task_id)
    assert task.status == "running"
    assert task.started_at is not None


def test_task_running_to_completed(test_space):
    """Task transitions from running → completed with output and duration."""
    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="list repos")
    spawn_db.update_task(task_id, status="running", started_at=True)

    output = "repo1\nrepo2\nrepo3"
    spawn_db.update_task(task_id, status="completed", output=output, completed_at=True)

    task = spawn_db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == output
    assert task.completed_at is not None
    assert task.duration is not None
    assert task.duration >= 0


def test_task_running_to_failed(test_space):
    """Task transitions from running → failed with stderr."""
    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="invalid command")
    spawn_db.update_task(task_id, status="running", started_at=True)

    stderr = "command not found"
    spawn_db.update_task(task_id, status="failed", stderr=stderr, completed_at=True)

    task = spawn_db.get_task(task_id)
    assert task.status == "failed"
    assert task.stderr == stderr
    assert task.output is None
    assert task.completed_at is not None


def test_task_pending_to_timeout(test_space):
    """Task can timeout without starting."""
    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="slow task")

    spawn_db.update_task(task_id, status="timeout", completed_at=True)
    task = spawn_db.get_task(task_id)
    assert task.status == "timeout"
    assert task.started_at is None
    assert task.completed_at is not None


def test_task_lifecycle_with_channel(test_space):
    """Task tracks channel_id for bridge integration."""
    spawn_db.ensure_agent("hailot")
    channel_id = "ch-spawn-test-123"
    task_id = spawn_db.create_task(
        identity="hailot",
        input="list repos",
        channel_id=channel_id,
    )

    task = spawn_db.get_task(task_id)
    assert task.channel_id == channel_id

    spawn_db.update_task(task_id, status="running", started_at=True)
    spawn_db.update_task(task_id, status="completed", output="done", completed_at=True)

    task = spawn_db.get_task(task_id)
    assert task.channel_id == channel_id
    assert task.status == "completed"


def test_multiple_tasks_per_identity(test_space):
    """Can track multiple concurrent tasks per agent."""
    spawn_db.ensure_agent("hailot")

    t1 = spawn_db.create_task(identity="hailot", input="task 1")
    t2 = spawn_db.create_task(identity="hailot", input="task 2")
    t3 = spawn_db.create_task(identity="hailot", input="task 3")

    spawn_db.update_task(t1, status="running", started_at=True)
    spawn_db.update_task(t2, status="running", started_at=True)

    hailot_tasks = spawn_db.list_tasks(identity="hailot")
    assert len(hailot_tasks) == 3

    running = spawn_db.list_tasks(status="running", identity="hailot")
    assert len(running) == 2
    assert {t.task_id for t in running} == {t1, t2}

    pending = spawn_db.list_tasks(status="pending", identity="hailot")
    assert len(pending) == 1
    assert pending[0].task_id == t3


def test_task_output_capture(test_space):
    """Tasks capture both stdout and stderr."""
    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="run with mixed output")

    spawn_db.update_task(task_id, status="running", started_at=True)
    spawn_db.update_task(
        task_id,
        status="completed",
        output="stdout content",
        stderr="stderr content",
        completed_at=True,
    )

    task = spawn_db.get_task(task_id)
    assert task.output == "stdout content"
    assert task.stderr == "stderr content"
