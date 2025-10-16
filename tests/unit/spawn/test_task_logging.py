from space.spawn import registry


def test_log_task(in_memory_db):
    """Log a task and verify it appears in tasks table."""
    identity = "hailot"
    output = "task completed successfully"
    con_hash = "abc123"

    task_id = registry.log_task(identity, output, constitution_hash=con_hash)

    assert task_id is not None
    assert len(task_id) > 0

    with registry.get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE uuid7 = ?", (task_id,)).fetchone()
        assert row is not None
        assert row["identity"] == identity
        assert row["output"] == output
        assert row["constitution_hash"] == con_hash
        assert row["channel"] is None
        assert row["completed_at"] is not None


def test_log_task_with_channel(in_memory_db):
    """Log a task with channel and verify it's tracked."""
    identity = "hailot"
    output = "response from channel task"
    con_hash = "hash123"
    channel = "subagents-test"

    task_id = registry.log_task(identity, output, constitution_hash=con_hash, channel=channel)

    with registry.get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE uuid7 = ?", (task_id,)).fetchone()
        assert row["channel"] == channel
        assert row["completed_at"] is not None


def test_log_task_minimal(in_memory_db):
    """Log task with minimal args."""
    task_id = registry.log_task("zealot", "done")

    with registry.get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE uuid7 = ?", (task_id,)).fetchone()
        assert row["identity"] == "zealot"
        assert row["output"] == "done"
        assert row["completed_at"] is not None
