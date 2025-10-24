"""Integration tests for bridge task tracking (tasks moved from spawn to bridge)."""

from unittest.mock import MagicMock, patch

from space.os.bridge import api as bridge_api
from space.os.bridge import db as bridge_db
from space.os.bridge import parser
from space.os.lib.uuid7 import uuid7


def test_channel_groups_tasks(test_space):
    """Tasks in same channel are grouped."""
    channel_id = bridge_api.create_channel("investigation-channel")

    conn = bridge_db.connect()
    for identity in ["hailot", "zealot", "hailot"]:
        conn.execute(
            """
            INSERT INTO tasks (uuid7, channel_id, identity, status, created_at)
            VALUES (?, ?, ?, 'completed', datetime('now'))
            """,
            (uuid7(), channel_id, identity),
        )
    conn.commit()
    conn.close()

    conn = bridge_db.connect()
    rows = conn.execute(
        "SELECT uuid7, identity FROM tasks WHERE channel_id = ? ORDER BY created_at",
        (channel_id,),
    ).fetchall()
    conn.close()

    assert len(rows) == 3
    assert [r["identity"] for r in rows] == ["hailot", "zealot", "hailot"]


def test_channel_isolation(test_space):
    """Tasks from different channels isolated."""
    channel_a = bridge_api.create_channel("channel-a")
    channel_b = bridge_api.create_channel("channel-b")

    conn = bridge_db.connect()
    conn.execute(
        "INSERT INTO tasks (uuid7, channel_id, identity, status, created_at) VALUES (?, ?, ?, 'completed', datetime('now'))",
        (uuid7(), channel_a, "hailot"),
    )
    conn.execute(
        "INSERT INTO tasks (uuid7, channel_id, identity, status, created_at) VALUES (?, ?, ?, 'completed', datetime('now'))",
        (uuid7(), channel_b, "zealot"),
    )
    conn.commit()
    conn.close()

    conn = bridge_db.connect()
    a_count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE channel_id = ?", (channel_a,)
    ).fetchone()[0]
    b_count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE channel_id = ?", (channel_b,)
    ).fetchone()[0]
    conn.close()

    assert a_count == 1
    assert b_count == 1


def test_retrieve_channel_history(test_space):
    """Retrieve full task history for channel."""
    channel_id = bridge_api.create_channel("investigation")
    tasks = [
        ("hailot", "started investigation"),
        ("zealot", "gathered data"),
        ("hailot", "final report"),
    ]

    conn = bridge_db.connect()
    for identity, output in tasks:
        conn.execute(
            """
            INSERT INTO tasks (uuid7, channel_id, identity, output, status, created_at)
            VALUES (?, ?, ?, ?, 'completed', datetime('now'))
            """,
            (uuid7(), channel_id, identity, output),
        )
    conn.commit()
    conn.close()

    conn = bridge_db.connect()
    rows = conn.execute(
        "SELECT identity, output FROM tasks WHERE channel_id = ? ORDER BY created_at",
        (channel_id,),
    ).fetchall()
    conn.close()

    assert len(rows) == 3
    for i, (identity, output) in enumerate(tasks):
        assert rows[i]["identity"] == identity
        assert rows[i]["output"] == output


def test_spawn_logs_metadata(test_space):
    """Bridge task stores all metadata (identity, channel, output, status)."""
    channel_id = bridge_api.create_channel("subagents-test")
    identity = "hailot"
    output = "response"
    task_id = uuid7()

    conn = bridge_db.connect()
    conn.execute(
        """
        INSERT INTO tasks (uuid7, channel_id, identity, output, status, created_at)
        VALUES (?, ?, ?, ?, 'completed', datetime('now'))
        """,
        (task_id, channel_id, identity, output),
    )
    conn.commit()

    row = conn.execute(
        "SELECT identity, channel_id, output, status FROM tasks WHERE uuid7 = ?",
        (task_id,),
    ).fetchone()
    conn.close()

    assert row["identity"] == identity
    assert row["channel_id"] == channel_id
    assert row["output"] == output
    assert row["status"] == "completed"


def test_mention_spawns_worker():
    """Bridge detects @mention and returns prompt for worker."""
    with patch("space.os.bridge.parser.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="# subagents-test\n\n[alice] hello\n"
        )

        results = parser.process_message("subagents-test", "@hailot question")

        assert len(results) == 1
        assert results[0][0] == "hailot"
        assert "[TASK INSTRUCTIONS]" in results[0][1]


def test_task_provenance_chain(test_space):
    """Task entry tracks full provenance: identity, channel_id, output, status, timestamps."""
    channel_id = bridge_api.create_channel("investigation")
    identity = "hailot"
    output = "findings"
    task_id = uuid7()

    conn = bridge_db.connect()
    conn.execute(
        """
        INSERT INTO tasks (uuid7, channel_id, identity, output, status, created_at, completed_at)
        VALUES (?, ?, ?, ?, 'completed', datetime('now'), datetime('now'))
        """,
        (task_id, channel_id, identity, output),
    )
    conn.commit()

    row = conn.execute(
        "SELECT uuid7, identity, channel_id, output, status, created_at, completed_at FROM tasks WHERE uuid7 = ?",
        (task_id,),
    ).fetchone()
    conn.close()

    assert row["uuid7"] == task_id
    assert row["identity"] == identity
    assert row["channel_id"] == channel_id
    assert row["output"] == output
    assert row["status"] == "completed"
    assert row["created_at"] is not None
    assert row["completed_at"] is not None
