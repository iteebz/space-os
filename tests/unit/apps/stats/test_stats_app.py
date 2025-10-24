"""Test agent stats discovery across all databases."""

import time

from space.apps import stats as stats_lib
from space.os.lib import paths


def test_discovers_registered_agents(test_space):
    """Active registered agents are discovered."""
    from space.os.core.spawn import db as spawn_db

    with spawn_db.connect() as conn:
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("agent-001", "alice"))

    result = stats_lib.agent_stats()
    assert result is not None
    assert len(result) == 1
    assert result[0].agent_id == "agent-001"
    assert result[0].agent_name == "alice"


def test_discovers_orphaned_agents_in_events(test_space):
    """Agents with events but no registration are discovered."""
    from space.os import events as events_lib

    events_lib.emit("test", "spawn", "orphan-001", "data")

    result = stats_lib.agent_stats()
    assert result is not None
    assert len(result) >= 1
    assert any(a.agent_id == "orphan-001" for a in result)
    agent = next(a for a in result if a.agent_id == "orphan-001")
    assert agent.agent_name == "orphan-001"


def test_discovers_orphaned_agents_in_messages(test_space):
    """Agents with messages but no registration are discovered."""
    from space.os import db

    paths.space_data() / "bridge.db"
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            ("msg-1", "chan-1", "msg-agent-001", "hello"),
        )

    result = stats_lib.agent_stats()
    assert result is not None
    assert any(a.agent_id == "msg-agent-001" for a in result)


def test_discovers_orphaned_agents_in_memory(test_space):
    """Agents with memories but no registration are discovered."""
    from space.os import db

    mem_db = paths.space_data() / "memory.db"
    with db.connect(mem_db) as conn:
        conn.execute(
            "INSERT INTO memories (memory_id, agent_id, topic, message, timestamp, created_at, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "mem-1",
                "mem-agent-001",
                "topic1",
                "content",
                "2024-01-01",
                int(time.time()),
                "test",
            ),
        )
        conn.commit()

    result = stats_lib.agent_stats()
    assert result is not None
    assert any(a.agent_id == "mem-agent-001" for a in result)


def test_discovers_orphaned_agents_in_knowledge(test_space):
    """Agents with knowledge but no registration are discovered."""
    from space.os import db

    know_db = paths.space_data() / "knowledge.db"
    with db.connect(know_db) as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, agent_id, domain, content) VALUES (?, ?, ?, ?)",
            ("know-1", "know-agent-001", "domain1", "content"),
        )
        conn.commit()

    result = stats_lib.agent_stats()
    assert result is not None
    assert any(a.agent_id == "know-agent-001" for a in result)


def test_maps_registered_name_to_orphaned_agent(test_space):
    """If orphaned agent is later registered, name is used."""
    from space.os import events as events_lib
    from space.os.core.spawn import db as spawn_db

    events_lib.emit("test", "spawn", "agent-xyz", "data")

    with spawn_db.connect() as conn:
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("agent-xyz", "bob"))

    result = stats_lib.agent_stats()
    agent = next(a for a in result if a.agent_id == "agent-xyz")
    assert agent.agent_name == "bob"


def test_aggregates_stats_from_all_tables(test_space):
    """Stats are aggregated from all tables for same agent."""
    from space.os import db
    from space.os import events as events_lib
    from space.os.core.spawn import db as spawn_db

    agent_id = "aggregator-001"

    with spawn_db.connect() as conn:
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", (agent_id, "agg"))

    events_lib.emit("test", "spawn", agent_id, "data")
    events_lib.emit("test", "session_start", agent_id, "data")

    paths.space_data() / "bridge.db"
    with db.ensure("bridge") as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            ("msg-1", "chan-1", agent_id, "msg1"),
        )
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            ("msg-2", "chan-1", agent_id, "msg2"),
        )

    paths.space_data() / "memory.db"
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


def test_respects_archived_filter(test_space):
    """Archived agents excluded by default, included with flag."""
    from space.os.core.spawn import db as spawn_db

    now = int(time.time())
    with spawn_db.connect() as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, name, archived_at) VALUES (?, ?, ?)",
            ("archived-001", "ghost", now),
        )
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("active-001", "alive"))

    result_active = stats_lib.agent_stats(include_archived=False)
    result_all = stats_lib.agent_stats(include_archived=True)

    active_ids = [a.agent_id for a in result_active or []]
    all_ids = [a.agent_id for a in result_all or []]

    assert "active-001" in active_ids
    assert "archived-001" not in active_ids
    assert "archived-001" in all_ids


def test_orphaned_agents_always_included(test_space):
    """Orphaned agents in activity logs always included (not registered, not archived)."""
    from space.os import events as events_lib
    from space.os.core.spawn import db as spawn_db

    now = int(time.time())
    with spawn_db.connect() as conn:
        conn.execute(
            "INSERT INTO agents (agent_id, name, archived_at) VALUES (?, ?, ?)",
            ("archived-001", "archived", now),
        )
        conn.execute("INSERT INTO agents (agent_id, name) VALUES (?, ?)", ("active-001", "active"))

    events_lib.emit("test", "spawn", "orphan-001", "data")

    result_active = stats_lib.agent_stats(include_archived=False)
    result_all = stats_lib.agent_stats(include_archived=True)

    active_ids = [a.agent_id for a in result_active or []]
    all_ids = [a.agent_id for a in result_all or []]

    assert len(active_ids) == 2, (
        f"Expected 2 active agents (active-001 + orphan-001), got {active_ids}"
    )
    assert "active-001" in active_ids
    assert "orphan-001" in active_ids
    assert "archived-001" not in active_ids

    assert len(all_ids) == 3, f"Expected 3 total agents, got {all_ids}"
    assert "active-001" in all_ids
    assert "orphan-001" in all_ids
    assert "archived-001" in all_ids


def test_discovery_counts_match_universe(test_space):
    """Active count excludes archived, --all includes archived."""
    from space.os import events as events_lib
    from space.os.core.spawn import db as spawn_db

    now = int(time.time())
    with spawn_db.connect() as conn:
        for i in range(3):
            conn.execute(
                "INSERT INTO agents (agent_id, name) VALUES (?, ?)",
                (f"active-{i:03d}", f"active{i}"),
            )
        for i in range(2):
            conn.execute(
                "INSERT INTO agents (agent_id, name, archived_at) VALUES (?, ?, ?)",
                (f"archived-{i:03d}", f"archived{i}", now),
            )

    for i in range(5):
        events_lib.emit("test", "spawn", f"orphan-{i:03d}", "data")

    result_active = stats_lib.agent_stats(include_archived=False)
    result_all = stats_lib.agent_stats(include_archived=True)

    active_count = len(result_active) if result_active else 0
    all_count = len(result_all) if result_all else 0

    assert active_count == 8, f"Active: 3 registered + 5 orphaned = 8, got {active_count}"
    assert all_count == 10, f"All: 3 active + 2 archived + 5 orphaned = 10, got {all_count}"
