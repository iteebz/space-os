"""Test agent stats discovery across all databases."""

import time

from space.apps import stats as stats_lib
from space.os.lib import paths


def test_discovers_registered_agents(test_space):
    from space.os import spawn

    with spawn.db.connect() as conn:
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("agent-001", "alice"))

    result = stats_lib.agent_stats()
    assert result is not None
    assert len(result) == 1
    assert result[0].agent_id == "agent-001"
    assert result[0].agent_name == "alice"


def test_discovers_orphaned_in_events(test_space):
    from space.os import events as events_lib

    events_lib.emit("test", "spawn", "orphan-001", "data")

    result = stats_lib.agent_stats()
    assert any(a.agent_id == "orphan-001" for a in result)


def test_discovers_orphaned_in_messages(test_space):
    from space.os import db

    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            ("msg-1", "chan-1", "msg-agent-001", "hello"),
        )

    result = stats_lib.agent_stats()
    assert any(a.agent_id == "msg-agent-001" for a in result)


def test_discovers_orphaned_in_memory(test_space):
    from space.os import db

    mem_db = paths.space_data() / "memory.db"
    with db.connect(mem_db) as conn:
        conn.execute(
            "INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("mem-1", "mem-agent-001", "topic1", "content", "2024-01-01", int(time.time()), "test"),
        )
        conn.commit()

    result = stats_lib.agent_stats()
    assert any(a.agent_id == "mem-agent-001" for a in result)


def test_maps_registration_name_to_orphan(test_space):
    from space.os import events as events_lib
    from space.os import spawn

    events_lib.emit("test", "spawn", "agent-xyz", "data")
    with spawn.db.connect() as conn:
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("agent-xyz", "bob"))

    result = stats_lib.agent_stats()
    agent = next(a for a in result if a.agent_id == "agent-xyz")
    assert agent.agent_name == "bob"


def test_aggregates_stats_from_all_sources(test_space):
    from space.os import db, spawn
    from space.os import events as events_lib

    agent_id = "aggregator-001"
    with spawn.db.connect() as conn:
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", (agent_id, "agg"))

    events_lib.emit("test", "spawn", agent_id, "data")
    events_lib.emit("test", "session_start", agent_id, "data")

    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            ("msg-1", "chan-1", agent_id, "msg1"),
        )
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            ("msg-2", "chan-1", agent_id, "msg2"),
        )

    with db.ensure("memory") as conn:
        conn.execute(
            "INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("mem-1", agent_id, "topic1", "mem", "2024-01-01", int(time.time()), "test"),
        )

    result = stats_lib.agent_stats()
    agent = next(a for a in result if a.agent_id == agent_id)

    assert agent.msgs == 2
    assert agent.mems == 1
    assert agent.spawns == 1
    assert agent.events >= 2


def test_archived_filter(test_space):
    from space.os import spawn

    now = int(time.time())
    with spawn.db.connect() as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, name, archived_at) VALUES (?, ?, ?)",
            ("archived-001", "ghost", now),
        )
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("active-001", "alive"))

    result_active = stats_lib.agent_stats(include_archived=False)
    result_all = stats_lib.agent_stats(include_archived=True)

    active_ids = {a.agent_id for a in (result_active or [])}
    all_ids = {a.agent_id for a in (result_all or [])}

    assert "active-001" in active_ids
    assert "archived-001" not in active_ids
    assert "archived-001" in all_ids


def test_orphaned_included_regardless_of_archived_flag(test_space):
    from space.os import events as events_lib
    from space.os import spawn

    now = int(time.time())
    with spawn.db.connect() as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, name, archived_at) VALUES (?, ?, ?)",
            ("archived-001", "archived", now),
        )
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("active-001", "active"))

    events_lib.emit("test", "spawn", "orphan-001", "data")

    result_active = stats_lib.agent_stats(include_archived=False)
    result_all = stats_lib.agent_stats(include_archived=True)

    active_ids = {a.agent_id for a in (result_active or [])}
    all_ids = {a.agent_id for a in (result_all or [])}

    assert "active-001" in active_ids
    assert "orphan-001" in active_ids
    assert "archived-001" not in active_ids

    assert "archived-001" in all_ids
    assert "orphan-001" in all_ids
