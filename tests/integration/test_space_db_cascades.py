from __future__ import annotations

from space.lib import store
from space.os import db as unified_db

TIMESTAMP = "2024-01-01T00:00:00.000000"


def test_channel_and_agent_cascades(test_space):
    unified_db.register()

    agent_id = "agent-alpha"
    channel_id = "channel-bridge"
    message_id = "message-1"
    bookmark_agent = agent_id
    task_id = "task-1"
    session_id = "session-1"
    parent_memory_id = "memory-parent"
    child_memory_id = "memory-child"
    link_id = "link-1"
    knowledge_id = "knowledge-1"

    with store.ensure("space") as conn:
        conn.execute(
            """
            INSERT INTO agents (agent_id, identity, model, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (agent_id, "alpha", "gpt-4", TIMESTAMP),
        )
        conn.execute(
            """
            INSERT INTO channels (channel_id, name, created_at)
            VALUES (?, ?, ?)
            """,
            (channel_id, "Bridge", TIMESTAMP),
        )
        conn.execute(
            """
            INSERT INTO messages (message_id, channel_id, agent_id, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, channel_id, agent_id, "ping", TIMESTAMP),
        )
        conn.execute(
            """
            INSERT INTO bookmarks (agent_id, channel_id, last_seen_id)
            VALUES (?, ?, ?)
            """,
            (bookmark_agent, channel_id, message_id),
        )
        conn.execute(
            """
            INSERT INTO tasks (task_id, agent_id, channel_id, input, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, agent_id, channel_id, "run command", TIMESTAMP),
        )
        conn.execute(
            """
            INSERT INTO sessions (session_id, agent_id, spawn_number, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, agent_id, 1, TIMESTAMP),
        )
        conn.execute(
            """
            INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, bridge_channel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (parent_memory_id, agent_id, "journal", "parent memory", TIMESTAMP, TIMESTAMP, channel_id),
        )
        conn.execute(
            """
            INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, bridge_channel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (child_memory_id, agent_id, "notes", "child memory", TIMESTAMP, TIMESTAMP, channel_id),
        )
        conn.execute(
            """
            UPDATE memories SET supersedes=?, superseded_by=? WHERE memory_id=?
            """,
            (parent_memory_id, child_memory_id, child_memory_id),
        )
        conn.execute(
            """
            INSERT INTO links (link_id, memory_id, parent_id, kind, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (link_id, child_memory_id, parent_memory_id, "derives", TIMESTAMP),
        )
        conn.execute(
            """
            INSERT INTO knowledge (knowledge_id, domain, agent_id, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (knowledge_id, "architecture", agent_id, "shared insight", TIMESTAMP),
        )

    with store.ensure("space") as conn:
        conn.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
        assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
        assert (
            conn.execute("SELECT channel_id FROM tasks WHERE task_id=?", (task_id,)).fetchone()[0]
            is None
        )
        assert (
            conn.execute(
                "SELECT bridge_channel FROM memories WHERE memory_id=?", (parent_memory_id,)
            ).fetchone()[0]
            is None
        )
        assert (
            conn.execute(
                "SELECT bridge_channel FROM memories WHERE memory_id=?", (child_memory_id,)
            ).fetchone()[0]
            is None
        )
        assert conn.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0] == 0

    with store.ensure("space") as conn:
        conn.execute("DELETE FROM agents WHERE agent_id=?", (agent_id,))
        for table in ("tasks", "sessions", "memories", "knowledge"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM links").fetchone()[0] == 0
