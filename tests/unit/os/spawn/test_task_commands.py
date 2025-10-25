"""Test spawn task CLI commands: tasks, logs, wait, kill."""

import time

from space.os import spawn


def test_tasks_list_empty(test_space, capsys):
    """spawn tasks with no tasks shows empty."""
    from space.os.core.spawn.commands.tasks import list_tasks

    list_tasks(None, None)
    captured = capsys.readouterr()
    assert "No tasks" in captured.out or len(captured.out) == 0


def test_tasks_list_shows_running(test_space, capsys):
    """spawn tasks lists running tasks with status, identity, duration."""
    from space.os.core.spawn.commands.tasks import list_tasks

    spawn.ensure_agent("zealot")
    t1 = spawn.create_task(role="zealot", input="task 1", channel_id="ch-1")
    spawn.update_task(t1, status="running", mark_started=True)

    list_tasks(None, None)
    captured = capsys.readouterr()
    assert "zealot" in captured.out
    assert "running" in captured.out


def test_tasks_list_filter_by_status(test_space, capsys):
    """spawn tasks --status pending shows only pending."""
    from space.os.core.spawn.commands.tasks import list_tasks

    spawn.ensure_agent("zealot")
    t1 = spawn.create_task(role="zealot", input="task 1")
    t2 = spawn.create_task(role="zealot", input="task 2")
    spawn.update_task(t1, status="completed")

    list_tasks(status="pending", role=None)
    captured = capsys.readouterr()
    assert t2[:8] in captured.out or "task 2" in captured.out
    assert "task 1" not in captured.out or t1[:8] not in captured.out


def test_tasks_list_filter_by_identity(test_space, capsys):
    """spawn tasks --identity zealot shows only zealot tasks."""
    from space.os.core.spawn.commands.tasks import list_tasks

    spawn.ensure_agent("zealot")
    spawn.ensure_agent("sentinel")
    spawn.create_task(role="zealot", input="zealot task")
    t2 = spawn.create_task(role="sentinel", input="sentinel task")

    list_tasks(status=None, role="zealot")
    captured = capsys.readouterr()
    assert "zealot" in captured.out
    assert "sentinel" not in captured.out or t2[:8] not in captured.out


def test_logs_shows_full_task_detail(test_space, capsys):
    """spawn logs <id> shows input, output, stderr, timestamps, duration."""
    from space.os.core.spawn.commands.tasks import logs

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="list repos")
    spawn.update_task(task_id, status="running", mark_started=True)
    time.sleep(0.01)
    spawn.update_task(task_id, status="completed", output="repo1\nrepo2", mark_completed=True)

    logs(task_id)
    captured = capsys.readouterr()
    assert "list repos" in captured.out
    assert "repo1" in captured.out
    assert "completed" in captured.out


def test_logs_shows_failed_task_stderr(test_space, capsys):
    """spawn logs shows stderr for failed tasks."""
    from space.os.core.spawn.commands.tasks import logs

    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="bad command")
    spawn.update_task(task_id, status="failed", stderr="error: not found", mark_completed=True)

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
