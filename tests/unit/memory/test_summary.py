from datetime import datetime

from space.lib.ids import uuid7
from space.memory import db
from space.spawn import registry


def _add_summary_at_time(agent_id: str, message: str, timestamp: int):
    ts = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO memory (uuid, agent_id, topic, message, timestamp, created_at, core, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (uuid7(), agent_id, "summary", message, ts, timestamp, 0, "manual"),
        )
        conn.commit()


def test_summaries_append(test_space):
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    _add_summary_at_time(agent_id, "First session summary", 1000)
    _add_summary_at_time(agent_id, "Second session summary", 2000)
    _add_summary_at_time(agent_id, "Third session summary", 3000)

    summaries = db.get_entries("test-agent", topic="summary")
    assert len(summaries) == 3
    assert summaries[0].message == "First session summary"
    assert summaries[1].message == "Second session summary"
    assert summaries[2].message == "Third session summary"


def test_summaries_empty(test_space):
    registry.init_db()
    registry.ensure_agent("test-agent")

    summaries = db.get_entries("test-agent", topic="summary")
    assert summaries == []


def test_summary_ordering(test_space):
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    for i in range(5):
        _add_summary_at_time(agent_id, f"Session {i}", 1000 + i * 100)

    summaries = db.get_entries("test-agent", topic="summary")
    created_times = [s.created_at for s in summaries]

    assert created_times == sorted(created_times)
