"""Test spawn task lifecycle: task creation, status transitions, output capture."""

from space.os import spawn


def test_task_pending_to_running(test_space):
    """Task records started_at when transitioning to running."""
    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="list repos")

    task = spawn.db.get_task(task_id)
    assert task.status == "pending"
    assert task.started_at is None

    spawn.db.update_task(task_id, status="running", mark_started=True)
    task = spawn.db.get_task(task_id)
    assert task.status == "running"
    assert task.started_at is not None


def test_task_running_to_completed(test_space):
    """Completed task captures output and duration."""
    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="list repos")
    spawn.db.update_task(task_id, status="running", mark_started=True)

    output = "repo1\nrepo2\nrepo3"
    spawn.db.update_task(task_id, status="completed", output=output, mark_completed=True)

    task = spawn.db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == output
    assert task.completed_at is not None
    assert task.duration is not None
    assert task.duration >= 0


def test_task_running_to_failed(test_space):
    """Failed task captures stderr and completion time."""
    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="invalid command")
    spawn.db.update_task(task_id, status="running", mark_started=True)

    stderr = "command not found"
    spawn.db.update_task(task_id, status="failed", stderr=stderr, mark_completed=True)

    task = spawn.db.get_task(task_id)
    assert task.status == "failed"
    assert task.stderr == stderr
    assert task.output is None
    assert task.completed_at is not None


def test_task_pending_to_timeout(test_space):
    """Timeout task skips started_at if never ran."""
    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="slow task")

    spawn.db.update_task(task_id, status="timeout", mark_completed=True)
    task = spawn.db.get_task(task_id)
    assert task.status == "timeout"
    assert task.started_at is None
    assert task.completed_at is not None


def test_task_lifecycle_with_channel(test_space):
    """Persist channel_id across task lifecycle."""
    spawn.db.ensure_agent("hailot")
    channel_id = "ch-spawn-test-123"
    task_id = spawn.db.create_task(
        role="hailot",
        input="list repos",
        channel_id=channel_id,
    )

    task = spawn.db.get_task(task_id)
    assert task.channel_id == channel_id

    spawn.db.update_task(task_id, status="running", mark_started=True)
    spawn.db.update_task(task_id, status="completed", output="done", mark_completed=True)

    task = spawn.db.get_task(task_id)
    assert task.channel_id == channel_id
    assert task.status == "completed"


def test_multiple_tasks_per_identity(test_space):
    """Filter tasks by status and identity."""
    spawn.db.ensure_agent("hailot")

    t1 = spawn.db.create_task(role="hailot", input="task 1")
    t2 = spawn.db.create_task(role="hailot", input="task 2")
    t3 = spawn.db.create_task(role="hailot", input="task 3")

    spawn.db.update_task(t1, status="running", mark_started=True)
    spawn.db.update_task(t2, status="running", mark_started=True)

    hailot_tasks = spawn.db.list_tasks(role="hailot")
    assert len(hailot_tasks) == 3

    running = spawn.db.list_tasks(status="running", role="hailot")
    assert len(running) == 2
    assert {t.task_id for t in running} == {t1, t2}

    pending = spawn.db.list_tasks(status="pending", role="hailot")
    assert len(pending) == 1
    assert pending[0].task_id == t3


def test_task_output_capture(test_space):
    """Capture stdout and stderr independently."""
    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="run with mixed output")

    spawn.db.update_task(task_id, status="running", mark_started=True)
    spawn.db.update_task(
        task_id,
        status="completed",
        output="stdout content",
        stderr="stderr content",
        mark_completed=True,
    )

    task = spawn.db.get_task(task_id)
    assert task.output == "stdout content"
    assert task.stderr == "stderr content"
