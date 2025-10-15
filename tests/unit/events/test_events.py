import sqlite3
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from space import events


@pytest.fixture
def in_memory_db():
    """Fixture for an in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(events.SCHEMA)
    # Apply migrations
    for _, migrate_func in events.events_migrations:
        migrate_func(conn)
    yield conn
    # No conn.close() here, pytest will handle cleanup


@pytest.fixture
def mock_db_path(tmp_path):
    """Mocks DB_PATH to use a temporary file."""
    mock_path = tmp_path / "events.db"
    with patch("space.events.DB_PATH", mock_path):
        yield mock_path


@pytest.fixture
def mock_connect(in_memory_db):
    @contextmanager
    def _mock_connect():
        yield in_memory_db

    with patch("space.events._connect", new=_mock_connect):
        yield


def test_emit_event(mock_db_path, mock_connect, in_memory_db):
    """Test that events can be emitted and stored."""
    events.emit(
        "test_source",
        "test_type",
        agent_id="test_agent",
        data="test_data",
        session_id="test_session",
    )

    cursor = in_memory_db.execute(
        "SELECT source, event_type, agent_id, data, session_id FROM events"
    )
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "test_source"
    assert result[1] == "test_type"
    assert result[2] == "test_agent"
    assert result[3] == "test_data"
    assert result[4] == "test_session"
