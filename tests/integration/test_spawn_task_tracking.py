"""Integration tests for spawn task tracking and bridge coordination."""

from unittest.mock import MagicMock, patch

from space.bridge import parser
from space.spawn import registry, spawn


def test_channel_groups_tasks(in_memory_db):
    """Tasks in same channel are grouped."""
    channel = "investigation-channel"
    registry.log_task("hailot", "started", channel=channel)
    registry.log_task("zealot", "analyzed", channel=channel)
    registry.log_task("hailot", "result", channel=channel)

    with registry.get_db() as conn:
        rows = conn.execute(
            "SELECT uuid7, identity FROM tasks WHERE channel = ? ORDER BY created_at",
            (channel,),
        ).fetchall()

    assert len(rows) == 3
    assert [r["identity"] for r in rows] == ["hailot", "zealot", "hailot"]


def test_channel_isolation(in_memory_db):
    """Tasks from different channels isolated."""
    registry.log_task("hailot", "msg1", channel="channel-a")
    registry.log_task("zealot", "msg2", channel="channel-b")

    with registry.get_db() as conn:
        a_count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE channel = ?", ("channel-a",)
        ).fetchone()[0]
        b_count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE channel = ?", ("channel-b",)
        ).fetchone()[0]

    assert a_count == 1
    assert b_count == 1


def test_retrieve_channel_history(in_memory_db):
    """Retrieve full task history for channel."""
    channel = "investigation"
    tasks = [
        ("hailot", "started investigation"),
        ("zealot", "gathered data"),
        ("hailot", "final report"),
    ]

    for identity, output in tasks:
        registry.log_task(identity, output, channel=channel)

    with registry.get_db() as conn:
        rows = conn.execute(
            "SELECT identity, output FROM tasks WHERE channel = ? ORDER BY created_at",
            (channel,),
        ).fetchall()

    assert len(rows) == 3
    for i, (identity, output) in enumerate(tasks):
        assert rows[i]["identity"] == identity
        assert rows[i]["output"] == output


def test_spawn_logs_metadata(in_memory_db):
    """CLI invocation logs task with all metadata."""
    identity = "hailot"
    channel = "subagents-test"
    output = "response"
    con_hash = "abc123def456"

    task_id = registry.log_task(identity, output, constitution_hash=con_hash, channel=channel)

    with registry.get_db() as conn:
        row = conn.execute(
            "SELECT identity, channel, output, constitution_hash FROM tasks WHERE uuid7 = ?",
            (task_id,),
        ).fetchone()

    assert row["identity"] == identity
    assert row["channel"] == channel
    assert row["output"] == output
    assert row["constitution_hash"] == con_hash


def test_mention_spawns_worker():
    """Bridge detects @mention and returns prompt for worker."""
    with patch("space.bridge.parser.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="# subagents-test\n\n[alice] hello\n"
        )

        results = parser.process_message("subagents-test", "@hailot question")

        assert len(results) == 1
        assert results[0][0] == "hailot"
        assert "[TASK INSTRUCTIONS]" in results[0][1]


def test_task_provenance_chain(in_memory_db):
    """Task entry tracks full provenance: identity, channel, hash, timestamp."""
    identity = "hailot"
    channel = "investigation"
    output = "findings"
    con_hash = spawn.hash_content("zealot constitution")

    task_id = registry.log_task(identity, output, constitution_hash=con_hash, channel=channel)

    with registry.get_db() as conn:
        row = conn.execute(
            "SELECT uuid7, identity, channel, output, constitution_hash, created_at, completed_at FROM tasks WHERE uuid7 = ?",
            (task_id,),
        ).fetchone()

    assert row["uuid7"] == task_id
    assert row["identity"] == identity
    assert row["channel"] == channel
    assert row["output"] == output
    assert row["constitution_hash"] == con_hash
    assert row["created_at"] is not None
    assert row["completed_at"] is not None
