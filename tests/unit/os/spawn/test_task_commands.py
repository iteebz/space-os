"""Test spawn task CLI commands: tasks, logs, wait, kill."""

import time

from space.os import spawn


def test_tasks_list_empty(test_space, capsys):
    """spawn tasks with no tasks shows empty."""
    from space.os.core.spawn.tasks import tasks

    tasks(None, None)
    captured = capsys.readouterr()
    assert "No tasks" in captured.out or len(captured.out) == 0


def test_tasks_list_shows_running(test_space, capsys):
    """spawn tasks lists running tasks with status, identity, duration."""
    from space.os.core.spawn.tasks import tasks

    spawn.db.ensure_agent("hailot")
    t1 = spawn.db.create_task(role="hailot", input="task 1", channel_id="ch-1")
    spawn.db.update_task(t1, status="running", mark_started=True)

    tasks(None, None)
    captured = capsys.readouterr()
    assert "hailot" in captured.out
    assert "running" in captured.out


def test_tasks_list_filter_by_status(test_space, capsys):
    """spawn tasks --status pending shows only pending."""
    from space.os.core.spawn.tasks import tasks

    spawn.db.ensure_agent("hailot")
    t1 = spawn.db.create_task(role="hailot", input="task 1")
    t2 = spawn.db.create_task(role="hailot", input="task 2")
    spawn.db.update_task(t1, status="completed")

    tasks(status="pending", role=None)
    captured = capsys.readouterr()
    assert t2[:8] in captured.out or "task 2" in captured.out
    assert "task 1" not in captured.out or t1[:8] not in captured.out


def test_tasks_list_filter_by_identity(test_space, capsys):
    """spawn tasks --identity hailot shows only hailot tasks."""
    from space.os.core.spawn.tasks import tasks

    spawn.db.ensure_agent("hailot")
    spawn.db.ensure_agent("zealot")
    spawn.db.create_task(role="hailot", input="hailot task")
    t2 = spawn.db.create_task(role="zealot", input="zealot task")

    tasks(status=None, role="hailot")
    captured = capsys.readouterr()
    assert "hailot" in captured.out
    assert "zealot" not in captured.out or t2[:8] not in captured.out


def test_logs_shows_full_task_detail(test_space, capsys):
    """spawn logs <id> shows input, output, stderr, timestamps, duration."""
    from space.os.core.spawn.tasks import logs

    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="list repos")
    spawn.db.update_task(task_id, status="running", mark_started=True)
    time.sleep(0.01)
    spawn.db.update_task(task_id, status="completed", output="repo1\nrepo2", mark_completed=True)

    logs(task_id)
    captured = capsys.readouterr()
    assert "list repos" in captured.out
    assert "repo1" in captured.out
    assert "completed" in captured.out


def test_logs_shows_failed_task_stderr(test_space, capsys):
    """spawn logs shows stderr for failed tasks."""
    from space.os.core.spawn.tasks import logs

    spawn.db.ensure_agent("hailot")
    task_id = spawn.db.create_task(role="hailot", input="bad command")
    spawn.db.update_task(task_id, status="failed", stderr="error: not found", mark_completed=True)

    logs(task_id)
    captured = capsys.readouterr()
    assert "bad command" in captured.out
    assert "error: not found" in captured.out


def test_logs_task_not_found(test_space, capsys):
    """spawn logs <invalid-id> shows error."""
    import typer

    from space.os.core.spawn.tasks import logs

    try:
        logs("nonexistent-id-123")
        raise AssertionError("Should have raised Exit")
    except typer.Exit as e:
        assert e.exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
