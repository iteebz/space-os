from space.os.spawn import registry, spawn


def test_save_get_agent_identity(in_memory_db):
    full_identity = "You are a test agent.\nSelf: I am a test.\n\nConstitution: Test."
    constitution_hash = spawn.hash_content(full_identity)

    registry.save_constitution(constitution_hash, full_identity)
    retrieved_identity = registry.get_constitution(constitution_hash)
    assert retrieved_identity == full_identity

    updated_full_identity = (
        "You are an updated test agent.\nSelf: I am updated.\n\nConstitution: Updated Test."
    )
    updated_constitution_hash = spawn.hash_content(updated_full_identity)
    registry.save_constitution(updated_constitution_hash, updated_full_identity)
    retrieved_updated_identity = registry.get_constitution(updated_constitution_hash)
    assert retrieved_updated_identity == updated_full_identity

    non_existent_identity = registry.get_constitution("nonexistenthash")
    assert non_existent_identity is None


def test_save_long_id(test_space):
    long_full_identity = "A" * 10000
    constitution_hash = spawn.hash_content(long_full_identity)

    registry.save_constitution(constitution_hash, long_full_identity)
    retrieved_identity = registry.get_constitution(constitution_hash)
    assert retrieved_identity == long_full_identity


def test_save_special_chars_id(test_space):
    special_char_identity = "Hello!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    constitution_hash = spawn.hash_content(special_char_identity)

    registry.save_constitution(constitution_hash, special_char_identity)
    retrieved_identity = registry.get_constitution(constitution_hash)
    assert retrieved_identity == special_char_identity


def test_create_task(in_memory_db):
    registry.ensure_agent("hailot")

    task_id = registry.create_task(
        identity="hailot",
        input="list repos",
        channel_id="ch-123",
    )

    assert task_id is not None
    task = registry.get_task(task_id)
    assert task["identity"] == "hailot"
    assert task["input"] == "list repos"
    assert task["channel_id"] == "ch-123"
    assert task["status"] == "pending"
    assert task["output"] is None
    assert task["stderr"] is None
    assert task["started_at"] is None
    assert task["completed_at"] is None


def test_update_task_status(in_memory_db):
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="test task")

    registry.update_task(task_id, status="running", started_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "running"
    assert task["started_at"] is not None


def test_complete_task(in_memory_db):
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="test task")
    registry.update_task(task_id, status="running", started_at=True)

    registry.update_task(task_id, status="completed", output="success", completed_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "completed"
    assert task["output"] == "success"
    assert task["completed_at"] is not None
    assert task["duration"] is not None


def test_fail_task(in_memory_db):
    registry.ensure_agent("hailot")
    task_id = registry.create_task(identity="hailot", input="test task")

    registry.update_task(task_id, status="failed", stderr="error message", completed_at=True)
    task = registry.get_task(task_id)
    assert task["status"] == "failed"
    assert task["stderr"] == "error message"


def test_list_tasks(in_memory_db):
    registry.ensure_agent("hailot")
    registry.ensure_agent("zealot")

    t1 = registry.create_task(identity="hailot", input="task 1")
    t2 = registry.create_task(identity="zealot", input="task 2")
    registry.update_task(t1, status="completed")

    all_tasks = registry.list_tasks()
    assert len(all_tasks) == 2

    pending = registry.list_tasks(status="pending")
    assert len(pending) == 1
    assert pending[0]["id"] == t2

    hailot_tasks = registry.list_tasks(identity="hailot")
    assert len(hailot_tasks) == 1
    assert hailot_tasks[0]["id"] == t1
