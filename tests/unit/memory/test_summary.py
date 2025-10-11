from datetime import datetime

from space.lib.ids import uuid7
from space.memory import db
from space.spawn import registry


def _add_summary_at_time(agent_id: str, message: str, timestamp: int):
    """Helper to add summary with specific timestamp."""
    ts = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

    with db.connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, agent_id, topic, message, timestamp, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid7(), agent_id, "summary", message, ts, timestamp, 0, "summary"),
        )
        conn.commit()


def test_set_summary_appends(test_space):
    """Summaries append, creating linked list."""
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    _add_summary_at_time(agent_id, "First session summary", 1000)
    _add_summary_at_time(agent_id, "Second session summary", 2000)
    _add_summary_at_time(agent_id, "Third session summary", 3000)

    summaries = db.get_summaries(agent_id)
    assert len(summaries) == 3
    assert summaries[0].message == "Third session summary"
    assert summaries[1].message == "Second session summary"
    assert summaries[2].message == "First session summary"


def test_get_summary_returns_most_recent(test_space):
    """get_summary returns most recent entry."""
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    _add_summary_at_time(agent_id, "Old summary", 1000)
    _add_summary_at_time(agent_id, "New summary", 2000)

    assert db.get_summary(agent_id) == "New summary"


def test_get_summaries_limits(test_space):
    """get_summaries respects limit."""
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    for i in range(10):
        _add_summary_at_time(agent_id, f"Summary {i}", 1000 + i * 100)

    summaries = db.get_summaries(agent_id, limit=3)
    assert len(summaries) == 3
    assert summaries[0].message == "Summary 9"
    assert summaries[1].message == "Summary 8"
    assert summaries[2].message == "Summary 7"


def test_get_summaries_empty(test_space):
    """get_summaries returns empty list when none exist."""
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    summaries = db.get_summaries(agent_id)
    assert summaries == []


def test_summary_linked_list_order(test_space):
    """Summaries ordered by created_at DESC (newest first)."""
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    for i in range(5):
        _add_summary_at_time(agent_id, f"Session {i}", 1000 + i * 100)

    summaries = db.get_summaries(agent_id)
    created_times = [s.created_at for s in summaries]

    assert created_times == sorted(created_times, reverse=True)
