"""Integration tests for spawn task tracking."""

from unittest.mock import MagicMock, patch

from space.os import spawn
from space.os.core.bridge import db as bridge_api
from space.os.core.bridge import worker
from space.os.lib.uuid7 import uuid7


def test_channel_groups_tasks(test_space):
    """Tasks in same channel are grouped."""
    channel_id = bridge_api.create_channel("investigation-channel")
    agent = spawn.db.ensure_agent("hailot")
    agent2 = spawn.db.ensure_agent("zealot")

    conn = spawn.db.connect().__enter__()
    for agent_id in [agent, agent2, agent]:
        conn.execute(
            """
            INSERT INTO tasks (task_id, agent_id, channel_id, input, status, created_at)
            VALUES (?, ?, ?, 'test', 'completed', datetime('now'))
            """,
            (uuid7(), agent_id, channel_id),
        )
    conn.commit()
    conn.close()

    conn = spawn.db.connect().__enter__()
    rows = conn.execute(
        "SELECT task_id, agent_id FROM tasks WHERE channel_id = ? ORDER BY created_at",
        (channel_id,),
    ).fetchall()
    conn.close()

    assert len(rows) == 3
    assert [spawn.db.get_agent_name(r["agent_id"]) for r in rows] == ["hailot", "zealot", "hailot"]


def test_channel_isolation(test_space):
    """Tasks from different channels isolated."""
    channel_a = bridge_api.create_channel("channel-a")
    channel_b = bridge_api.create_channel("channel-b")
    agent1 = spawn.db.ensure_agent("hailot")
    agent2 = spawn.db.ensure_agent("zealot")

    conn = spawn.db.connect().__enter__()
    conn.execute(
        "INSERT INTO tasks (task_id, agent_id, channel_id, input, status, created_at) VALUES (?, ?, ?, 'test', 'completed', datetime('now'))",
        (uuid7(), agent1, channel_a),
    )
    conn.execute(
        "INSERT INTO tasks (task_id, agent_id, channel_id, input, status, created_at) VALUES (?, ?, ?, 'test', 'completed', datetime('now'))",
        (uuid7(), agent2, channel_b),
    )
    conn.commit()
    conn.close()

    conn = spawn.db.connect().__enter__()
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
    agent_hailot = spawn.db.ensure_agent("hailot")
    agent_zealot = spawn.db.ensure_agent("zealot")

    tasks = [
        (agent_hailot, "started investigation"),
        (agent_zealot, "gathered data"),
        (agent_hailot, "final report"),
    ]

    conn = spawn.db.connect().__enter__()
    for agent_id, output in tasks:
        conn.execute(
            """
            INSERT INTO tasks (task_id, agent_id, channel_id, input, output, status, created_at)
            VALUES (?, ?, ?, 'test', ?, 'completed', datetime('now'))
            """,
            (uuid7(), agent_id, channel_id, output),
        )
    conn.commit()
    conn.close()

    conn = spawn.db.connect().__enter__()
    rows = conn.execute(
        "SELECT agent_id, output FROM tasks WHERE channel_id = ? ORDER BY created_at",
        (channel_id,),
    ).fetchall()
    conn.close()

    assert len(rows) == 3
    for i, (agent_id, output) in enumerate(tasks):
        assert spawn.db.get_agent_name(rows[i]["agent_id"]) == spawn.db.get_agent_name(agent_id)
        assert rows[i]["output"] == output


def test_spawn_logs_metadata(test_space):
    """Spawn task stores all metadata (agent, channel, output, status)."""
    channel_id = bridge_api.create_channel("subagents-test")
    agent = spawn.db.ensure_agent("hailot")
    output = "response"
    task_id = uuid7()

    conn = spawn.db.connect().__enter__()
    conn.execute(
        """
        INSERT INTO tasks (task_id, agent_id, channel_id, input, output, status, created_at)
        VALUES (?, ?, ?, 'test', ?, 'completed', datetime('now'))
        """,
        (task_id, agent, channel_id, output),
    )
    conn.commit()

    row = conn.execute(
        "SELECT agent_id, channel_id, output, status FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    conn.close()

    assert spawn.db.get_agent_name(row["agent_id"]) == "hailot"
    assert row["channel_id"] == channel_id
    assert row["output"] == output
    assert row["status"] == "completed"


def test_mention_spawns_worker():
    """Bridge detects @mention and returns prompt for worker."""
    with (
        patch("space.os.core.bridge.worker.subprocess.run") as mock_run,
        patch("space.os.core.bridge.worker.config.load_config") as mock_config,
    ):
        mock_config.return_value = {"roles": {"hailot": {}}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout="# subagents-test\n\n[alice] hello\n"
        )

        result = worker._build_prompt("hailot", "subagents-test", "@hailot question")

        assert result is not None
        assert "[SPACE INSTRUCTIONS]" in result


def test_task_provenance_chain(test_space):
    """Task entry tracks full provenance: agent_id, channel_id, output, status, timestamps."""
    channel_id = bridge_api.create_channel("investigation")
    agent = spawn.db.ensure_agent("hailot")
    output = "findings"
    task_id = uuid7()

    conn = spawn.db.connect().__enter__()
    conn.execute(
        """
        INSERT INTO tasks (task_id, agent_id, channel_id, input, output, status, created_at, completed_at)
        VALUES (?, ?, ?, 'test', ?, 'completed', datetime('now'), datetime('now'))
        """,
        (task_id, agent, channel_id, output),
    )
    conn.commit()

    row = conn.execute(
        "SELECT task_id, agent_id, channel_id, output, status, created_at, completed_at FROM tasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    conn.close()

    assert row["task_id"] == task_id
    assert spawn.db.get_agent_name(row["agent_id"]) == "hailot"
    assert row["channel_id"] == channel_id
    assert row["output"] == output
    assert row["status"] == "completed"
    assert row["created_at"] is not None
    assert row["completed_at"] is not None
