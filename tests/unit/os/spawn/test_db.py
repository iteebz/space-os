from space.os.core.spawn import db, hash_content


def test_save_get_agent_identity(test_space):
    full_identity = "You are a test agent.\nSelf: I am a test.\n\nConstitution: Test."
    constitution_hash = hash_content(full_identity)

    db.save_constitution(constitution_hash, full_identity)
    retrieved_identity = db.get_constitution(constitution_hash)
    assert retrieved_identity == full_identity

    updated_full_identity = (
        "You are an updated test agent.\nSelf: I am updated.\n\nConstitution: Updated Test."
    )
    updated_constitution_hash = hash_content(updated_full_identity)
    db.save_constitution(updated_constitution_hash, updated_full_identity)
    retrieved_updated_identity = db.get_constitution(updated_constitution_hash)
    assert retrieved_updated_identity == updated_full_identity

    non_existent_identity = db.get_constitution("nonexistenthash")
    assert non_existent_identity is None


def test_save_long_id(test_space):
    long_full_identity = "A" * 10000
    constitution_hash = hash_content(long_full_identity)

    db.save_constitution(constitution_hash, long_full_identity)
    retrieved_identity = db.get_constitution(constitution_hash)
    assert retrieved_identity == long_full_identity


def test_save_special_chars_id(test_space):
    special_char_identity = "Hello!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    constitution_hash = hash_content(special_char_identity)

    db.save_constitution(constitution_hash, special_char_identity)
    retrieved_identity = db.get_constitution(constitution_hash)
    assert retrieved_identity == special_char_identity


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

    db.update_task(task_id, status="running", started_at=True)
    task = db.get_task(task_id)
    assert task.status == "running"
    assert task.started_at is not None


def test_complete_task(test_space):
    db.ensure_agent("hailot")
    task_id = db.create_task(identity="hailot", input="test task")
    db.update_task(task_id, status="running", started_at=True)

    db.update_task(task_id, status="completed", output="success", completed_at=True)
    task = db.get_task(task_id)
    assert task.status == "completed"
    assert task.output == "success"
    assert task.completed_at is not None
    assert task.duration is not None


def test_fail_task(test_space):
    db.ensure_agent("hailot")
    task_id = db.create_task(identity="hailot", input="test task")

    db.update_task(task_id, status="failed", stderr="error message", completed_at=True)
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
