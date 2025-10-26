import time

from space.os import spawn


def test_wait_blocks_until_completion(test_space, default_agents):
    import threading

    from space.os.spawn.commands.tasks import wait

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="test")

    spawn.start_task(task_id)

    def complete_task_in_thread():
        time.sleep(0.1)
        spawn.complete_task(task_id, output="done")

    thread = threading.Thread(target=complete_task_in_thread)
    thread.start()

    exit_code = wait(task_id)
    assert exit_code == 0
    thread.join()


def test_wait_exit_code(test_space, default_agents):
    from space.os.spawn.commands.tasks import wait

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="test")
    spawn.fail_task(task_id)

    exit_code = wait(task_id)
    assert exit_code != 0


def test_wait_timeout(test_space, default_agents):
    import typer

    from space.os.spawn.commands.tasks import wait

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="test")
    spawn.start_task(task_id)

    try:
        wait(task_id, timeout=0.01)
        raise AssertionError("Should timeout")
    except typer.Exit as e:
        assert e.exit_code == 124


def test_wait_pending(test_space, default_agents):
    from space.os.spawn.commands.tasks import wait

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="test")

    spawn.start_task(task_id)
    spawn.complete_task(task_id, output="result")

    exit_code = wait(task_id)
    assert exit_code == 0

    task = spawn.get_task(task_id)
    assert task.output == "result"


def test_kill_running_task(test_space, default_agents):
    from space.os.spawn.commands.tasks import kill

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="long task")
    spawn.start_task(task_id, pid=12345)

    kill(task_id)

    task = spawn.get_task(task_id)
    assert task.status == "failed"
    assert "killed" in task.stderr.lower()


def test_kill_nonexistent_task(test_space, capsys):
    import typer

    from space.os.spawn.commands.tasks import kill

    try:
        kill("nonexistent-id")
        raise AssertionError("Should raise Exit")
    except typer.Exit as e:
        assert e.exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


def test_kill_completed_task_no_op(test_space, default_agents):
    from space.os.spawn.commands.tasks import kill

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="test")
    spawn.complete_task(task_id, output="done")

    kill(task_id)

    task = spawn.get_task(task_id)
    assert task.status == "completed"


def test_tasks_list_empty(test_space, capsys):
    from space.os.spawn.commands.tasks import list as list_tasks

    list_tasks(None, None)
    captured = capsys.readouterr()
    assert "No tasks" in captured.out or len(captured.out) == 0


def test_tasks_list_shows_running(test_space, capsys, default_agents):
    from space.os.spawn.commands.tasks import list as list_tasks

    zealot_id = default_agents["zealot"]
    t1 = spawn.create_task(role=zealot_id, input="task 1", channel_id="ch-1")
    spawn.start_task(t1)

    list_tasks(None, None)
    captured = capsys.readouterr()
    assert t1[:8] in captured.out
    assert "running" in captured.out


def test_tasks_list_filter_by_status(test_space, capsys, default_agents):
    from space.os.spawn.commands.tasks import list as list_tasks

    zealot_id = default_agents["zealot"]
    t1 = spawn.create_task(role=zealot_id, input="task 1")
    t2 = spawn.create_task(role=zealot_id, input="task 2")
    spawn.complete_task(t1)

    list_tasks(status="pending", role=None)
    captured = capsys.readouterr()
    assert t2[:8] in captured.out or "task 2" in captured.out
    assert "task 1" not in captured.out or t1[:8] not in captured.out


def test_tasks_list_filter_by_identity(test_space, capsys, default_agents):
    from space.os.spawn.commands.tasks import list as list_tasks

    sentinel_id = default_agents["sentinel"]
    zealot_id = default_agents["zealot"]
    spawn.create_task(role=zealot_id, input="zealot task")
    spawn.create_task(role=sentinel_id, input="sentinel task")

    list_tasks(status=None, role=zealot_id)
    captured = capsys.readouterr()
    lines = [
        line
        for line in captured.out.split("\n")
        if line.strip() and not line.startswith("ID") and line != "-" * 70
    ]
    assert len(lines) == 1


def test_logs_shows_full_task_detail(test_space, capsys, default_agents):
    from space.os.spawn.commands.tasks import logs

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="list repos")
    spawn.start_task(task_id)
    time.sleep(0.01)
    spawn.complete_task(task_id, output="repo1\nrepo2")

    logs(task_id)
    captured = capsys.readouterr()
    assert "list repos" in captured.out
    assert "repo1" in captured.out
    assert "completed" in captured.out


def test_logs_shows_failed_task_stderr(test_space, capsys, default_agents):
    from space.os.spawn.commands.tasks import logs

    zealot_id = default_agents["zealot"]
    task_id = spawn.create_task(role=zealot_id, input="bad command")
    spawn.fail_task(task_id, stderr="error: not found")

    logs(task_id)
    captured = capsys.readouterr()
    assert "bad command" in captured.out
    assert "error: not found" in captured.out


def test_logs_task_not_found(test_space, capsys):
    import typer

    from space.os.spawn.commands.tasks import logs

    try:
        logs("nonexistent-id-123")
        raise AssertionError("Should have raised Exit")
    except typer.Exit as e:
        assert e.exit_code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
