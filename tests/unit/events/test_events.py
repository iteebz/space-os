import sqlite3
from unittest.mock import patch

import pytest

from space.os import events


@pytest.fixture
def in_memory_db():
    """Fixture for an in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.executescript(events.SCHEMA)
    yield conn
    conn.close()


@pytest.fixture
def mock_db_path(tmp_path):
    """Mocks DB_PATH to use a temporary file."""
    mock_path = tmp_path / "events.db"
    with patch("space.os.events.DB_PATH", mock_path):
        yield mock_path


@pytest.fixture
def mock_ensure(in_memory_db):
    """Mock db.ensure to return in-memory database."""
    with patch("space.os.db.ensure") as mock:
        mock.return_value = in_memory_db
        yield mock


def test_emit_event(mock_db_path, mock_ensure, in_memory_db):
    events.emit(
        "test_source",
        "test_type",
        agent_id="test_agent",
        data="test_data",
    )

    cursor = in_memory_db.execute("SELECT source, event_type, agent_id, data FROM events")
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "test_source"
    assert result[1] == "test_type"
    assert result[2] == "test_agent"
    assert result[3] == "test_data"


def test_query_events(mock_db_path, mock_ensure, in_memory_db):
    in_memory_db.execute(
        "INSERT INTO events (id, source, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
        ("1", "test_src", "test_type", "data1", 1000, "agent1"),
    )
    in_memory_db.execute(
        "INSERT INTO events (id, source, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
        ("2", "other_src", "other_type", "data2", 2000, "agent2"),
    )

    with patch("space.os.events.DB_PATH", mock_db_path):
        mock_db_path.touch()
        results = events.query(source="test_src")
        assert len(results) == 1
        assert results[0].source == "test_src"
