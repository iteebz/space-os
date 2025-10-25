"""Test spawn wait and kill commands."""

import time

from space.os import spawn


def test_wait_blocks_until_completion(test_space):
    """spawn wait <id> blocks until task completes."""
    from space.os.core.spawn.commands.tasks import wait

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="test")

    spawn.update_task(task_id, status="running", mark_started=True)
    time.sleep(0.01)
    spawn.update_task(task_id, status="completed", output="done", mark_completed=True)

    exit_code = wait(task_id)
    assert exit_code == 0


def test_wait_exit_code(test_space):
    """spawn wait returns 0 for completed, non-zero for failed."""
    from space.os.core.spawn.commands.tasks import wait

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="test")
    spawn.update_task(task_id, status="failed", mark_completed=True)

    exit_code = wait(task_id)
    assert exit_code != 0


def test_wait_timeout(test_space):
    """spawn wait <id> --timeout raises error if exceeded."""
    import typer

    from space.os.core.spawn.commands.tasks import wait

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="slow task")
    spawn.update_task(task_id, status="running", mark_started=True)

    try:
        wait(task_id, timeout=0.01)
        raise AssertionError("Should timeout")
    except typer.Exit as e:
        assert e.exit_code == 124


def test_wait_pending(test_space):
    """spawn wait on pending task waits for it to start and complete."""
    from space.os.core.spawn.commands.tasks import wait

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="test")

    spawn.update_task(task_id, status="running", mark_started=True)
    spawn.update_task(task_id, status="completed", output="result", mark_completed=True)

    exit_code = wait(task_id)
    assert exit_code == 0

    task = spawn.get_task(task_id)
    assert task.output == "result"


def test_kill_running_task(test_space):
    """spawn kill <id> marks task as killed."""
    from space.os.core.spawn.commands.tasks import kill

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="long task")
    spawn.update_task(task_id, status="running", mark_started=True, pid=12345)

    kill(task_id)

    task = spawn.get_task(task_id)
    assert task.status == "failed"
    assert "killed" in task.stderr.lower()


def test_kill_nonexistent_task(test_space, capsys):
    """spawn kill <invalid-id> shows error."""
    import typer

    from space.os.core.spawn.commands.tasks import kill

    try:
        kill("nonexistent-id")
        raise AssertionError("Should raise Exit")
    except typer.Exit as e:
        assert e.exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


def test_kill_completed_task_no_op(test_space):
    """spawn kill on completed task is no-op."""
    from space.os.core.spawn.commands.tasks import kill

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="test")
    spawn.update_task(task_id, status="completed", output="done", mark_completed=True)

    kill(task_id)

    task = spawn.get_task(task_id)
    assert task.status == "completed"


def test_task_pid_tracking(test_space):
    """Tasks can track process ID for kill signal."""
    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="test")

    spawn.update_task(task_id, status="running", mark_started=True, pid=54321)

    task = spawn.get_task(task_id)
    assert task.pid == 54321
