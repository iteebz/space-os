"""Test spawn wait and kill commands."""

import time

from space.os.spawn import db as spawn_db


def test_wait_blocks_until_completion(test_space):
    """spawn wait <id> blocks until task completes."""
    from space.os.spawn.commands.tasks import wait_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="test")

    spawn_db.update_task(task_id, status="running", started_at=True)
    time.sleep(0.01)
    spawn_db.update_task(task_id, status="completed", output="done", completed_at=True)

    exit_code = wait_cmd(task_id)
    assert exit_code == 0


def test_wait_returns_task_status_as_exit_code(test_space):
    """spawn wait returns 0 for completed, non-zero for failed."""
    from space.os.spawn.commands.tasks import wait_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="test")
    spawn_db.update_task(task_id, status="failed", completed_at=True)

    exit_code = wait_cmd(task_id)
    assert exit_code != 0


def test_wait_timeout(test_space):
    """spawn wait <id> --timeout raises error if exceeded."""
    import typer

    from space.os.spawn.commands.tasks import wait_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="slow task")
    spawn_db.update_task(task_id, status="running", started_at=True)

    try:
        wait_cmd(task_id, timeout=0.01)
        raise AssertionError("Should timeout")
    except typer.Exit as e:
        assert e.exit_code == 124


def test_wait_pending_task_waits(test_space):
    """spawn wait on pending task waits for it to start and complete."""
    from space.os.spawn.commands.tasks import wait_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="test")

    spawn_db.update_task(task_id, status="running", started_at=True)
    spawn_db.update_task(task_id, status="completed", output="result", completed_at=True)

    exit_code = wait_cmd(task_id)
    assert exit_code == 0

    task = spawn_db.get_task(task_id)
    assert task.output == "result"


def test_kill_running_task(test_space):
    """spawn kill <id> marks task as killed."""
    from space.os.spawn.commands.tasks import kill_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="long task")
    spawn_db.update_task(task_id, status="running", started_at=True, pid=12345)

    kill_cmd(task_id)

    task = spawn_db.get_task(task_id)
    assert task.status == "failed"
    assert "killed" in task.stderr.lower()


def test_kill_nonexistent_task(test_space, capsys):
    """spawn kill <invalid-id> shows error."""
    import typer

    from space.os.spawn.commands.tasks import kill_cmd

    try:
        kill_cmd("nonexistent-id")
        raise AssertionError("Should raise Exit")
    except typer.Exit as e:
        assert e.exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


def test_kill_completed_task_no_op(test_space):
    """spawn kill on completed task is no-op."""
    from space.os.spawn.commands.tasks import kill_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="test")
    spawn_db.update_task(task_id, status="completed", output="done", completed_at=True)

    kill_cmd(task_id)

    task = spawn_db.get_task(task_id)
    assert task.status == "completed"


def test_task_pid_tracking(test_space):
    """Tasks can track process ID for kill signal."""
    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="test")

    spawn_db.update_task(task_id, status="running", started_at=True, pid=54321)

    task = spawn_db.get_task(task_id)
    assert task.pid == 54321
