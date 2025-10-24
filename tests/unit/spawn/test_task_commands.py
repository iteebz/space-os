"""Test spawn task CLI commands: tasks, logs, wait, kill."""

import time

from space.os.spawn import db as spawn_db


def test_tasks_list_empty(in_memory_db, capsys):
    """spawn tasks with no tasks shows empty."""
    from space.os.spawn.commands.tasks import tasks_cmd

    tasks_cmd(None, None)
    captured = capsys.readouterr()
    assert "No tasks" in captured.out or len(captured.out) == 0


def test_tasks_list_shows_running(in_memory_db, capsys):
    """spawn tasks lists running tasks with status, identity, duration."""
    from space.os.spawn.commands.tasks import tasks_cmd

    spawn_db.ensure_agent("hailot")
    t1 = spawn_db.create_task(identity="hailot", input="task 1", channel_id="ch-1")
    spawn_db.update_task(t1, status="running", started_at=True)

    tasks_cmd(None, None)
    captured = capsys.readouterr()
    assert "hailot" in captured.out
    assert "running" in captured.out


def test_tasks_list_filter_by_status(in_memory_db, capsys):
    """spawn tasks --status pending shows only pending."""
    from space.os.spawn.commands.tasks import tasks_cmd

    spawn_db.ensure_agent("hailot")
    t1 = spawn_db.create_task(identity="hailot", input="task 1")
    t2 = spawn_db.create_task(identity="hailot", input="task 2")
    spawn_db.update_task(t1, status="completed")

    tasks_cmd(status="pending", identity=None)
    captured = capsys.readouterr()
    assert t2[:8] in captured.out or "task 2" in captured.out
    assert "task 1" not in captured.out or t1[:8] not in captured.out


def test_tasks_list_filter_by_identity(in_memory_db, capsys):
    """spawn tasks --identity hailot shows only hailot tasks."""
    from space.os.spawn.commands.tasks import tasks_cmd

    spawn_db.ensure_agent("hailot")
    spawn_db.ensure_agent("zealot")
    spawn_db.create_task(identity="hailot", input="hailot task")
    t2 = spawn_db.create_task(identity="zealot", input="zealot task")

    tasks_cmd(status=None, identity="hailot")
    captured = capsys.readouterr()
    assert "hailot" in captured.out
    assert "zealot" not in captured.out or t2[:8] not in captured.out


def test_logs_shows_full_task_detail(in_memory_db, capsys):
    """spawn logs <id> shows input, output, stderr, timestamps, duration."""
    from space.os.spawn.commands.tasks import logs_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="list repos")
    spawn_db.update_task(task_id, status="running", started_at=True)
    time.sleep(0.01)
    spawn_db.update_task(task_id, status="completed", output="repo1\nrepo2", completed_at=True)

    logs_cmd(task_id)
    captured = capsys.readouterr()
    assert "list repos" in captured.out
    assert "repo1" in captured.out
    assert "completed" in captured.out


def test_logs_shows_failed_task_stderr(in_memory_db, capsys):
    """spawn logs shows stderr for failed tasks."""
    from space.os.spawn.commands.tasks import logs_cmd

    spawn_db.ensure_agent("hailot")
    task_id = spawn_db.create_task(identity="hailot", input="bad command")
    spawn_db.update_task(task_id, status="failed", stderr="error: not found", completed_at=True)

    logs_cmd(task_id)
    captured = capsys.readouterr()
    assert "bad command" in captured.out
    assert "error: not found" in captured.out


def test_logs_task_not_found(in_memory_db, capsys):
    """spawn logs <invalid-id> shows error."""
    import typer

    from space.os.spawn.commands.tasks import logs_cmd

    try:
        logs_cmd("nonexistent-id-123")
        raise AssertionError("Should have raised Exit")
    except typer.Exit as e:
        assert e.exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
