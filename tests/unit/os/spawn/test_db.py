from space.os.core.spawn import db


def test_create_task(test_space):
    db.ensure_agent("hailot")

    task_id = db.create_task(
        identity="hailot",
        input="list repos",
        channel_id="ch-123",
    )

    assert task_id is not None
    task = db.get_task(task_id)
    assert task.agent_id is not None
    assert task.input == "list repos"
    assert task.channel_id == "ch-123"
    assert task.status == "pending"
    assert task.output is None
    assert task.stderr is None
    assert task.started_at is None
    assert task.completed_at is None


def test_update_task_status(test_space):
    db.ensure_agent("hailot")
    task_id = db.create_task(identity="hailot", input="test task")

    db.update_task(task_id, status="running", mark_started=True)
    task = db.get_task(task_id)
    assert task.status == "running"
    assert task.started_at is not None


def test_complete_task(test_space):
    db.ensure_agent("hailot")
    task_id = db.create_task(identity="hailot", input="test task")
    db.update_task(task_id, status="running", mark_started=True)

    db.update_task(task_id, status="completed", output="success", mark_completed=True)
    task = db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == "success"
    assert task.completed_at is not None
    assert task.duration is not None


def test_fail_task(test_space):
    db.ensure_agent("hailot")
    task_id = db.create_task(identity="hailot", input="test task")

    db.update_task(task_id, status="failed", stderr="error message", mark_completed=True)
    task = db.get_task(task_id)
    assert task.status == "failed"
    assert task.stderr == "error message"


def test_list_tasks(test_space):
    db.ensure_agent("hailot")
    db.ensure_agent("zealot")

    t1 = db.create_task(identity="hailot", input="task 1")
    t2 = db.create_task(identity="zealot", input="task 2")
    db.update_task(t1, status="completed")

    all_tasks = db.list_tasks()
    assert len(all_tasks) == 2

    pending = db.list_tasks(status="pending")
    assert len(pending) == 1
    assert pending[0].task_id == t2

    hailot_tasks = db.list_tasks(identity="hailot")
    assert len(hailot_tasks) == 1
    assert hailot_tasks[0].task_id == t1
