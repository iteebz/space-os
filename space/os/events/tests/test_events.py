from unittest.mock import patch, MagicMock
import pytest
import sqlite3
from datetime import datetime
from contextlib import contextmanager

from space.os.events.repo import EventRepo
from space.os.events.models import Event
from space.os.events.events import track, emit, on

@pytest.fixture
def event_repo() -> EventRepo:
    """Provides an EventRepo instance with a single, persistent in-memory SQLite connection for testing."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            event_type TEXT NOT NULL,
            identity TEXT,
            data TEXT,
            timestamp INTEGER NOT NULL
        )
    """
    )
    conn.commit()

    repo = EventRepo()

    @contextmanager
    def mock_get_db_connection(*args, **kwargs):
        yield conn

    with patch.object(repo, 'get_db_connection', mock_get_db_connection):
        yield repo

    conn.close()

class TestEventRepo:
    def test_add_and_get_all(self, event_repo: EventRepo):
        assert event_repo.get_all() == []

        with patch('space.os.lib.uuid7.uuid7', return_value="event-uuid-1"):
            event_repo.add("source1", "type1", "id1", {"key": "value"})

        events = event_repo.get_all()
        assert len(events) == 1
        event = events[0]
        assert event.id == "event-uuid-1"
        assert event.source == "source1"
        assert event.event_type == "type1"
        assert event.identity == "id1"
        assert event.data == {"key": "value"}
        assert isinstance(event.timestamp, int)

class TestEventsModule:
    @pytest.fixture(autouse=True)
    def clear_listeners(self):
        # Clear listeners before each test to ensure isolation
        from space.os.events.events import _listeners
        _listeners.clear()
        yield

    @patch('space.os.events.events._event_repo')
    @patch('space.os.lib.uuid7.uuid7', return_value="mock-uuid") # Corrected patch target here
    @patch('space.os.events.events.datetime')
    def test_track_records_and_emits(self, mock_datetime: MagicMock, mock_uuid: MagicMock, mock_event_repo: MagicMock):
        mock_datetime.now.return_value.timestamp.return_value = 1234567890.0
        mock_listener = MagicMock()
        on("test_type", "test_source")(mock_listener)

        track("test_source", "test_type", "test_identity", {"data_key": "data_value"})

        mock_event_repo.add.assert_called_once_with(
            "test_source",
            "test_type",
            "test_identity",
            {"data_key": "data_value"}
        )
        mock_listener.assert_called_once()
        called_event = mock_listener.call_args[0][0]
        assert called_event.id == "mock-uuid"
        assert called_event.timestamp == 1234567890
        assert called_event.source == "test_source"
        assert called_event.event_type == "test_type"
        assert called_event.identity == "test_identity"
        assert called_event.data == {"data_key": "data_value"}

    def test_on_decorator_registers_listener(self):
        mock_listener = MagicMock()
        @on("test_type", "test_source")
        def my_listener(event: Event):
            mock_listener(event)

        event = Event(id="1", timestamp=1, source="test_source", event_type="test_type")
        emit(event)

        mock_listener.assert_called_once_with(event)

    def test_on_decorator_registers_multiple_listeners(self):
        mock_listener1 = MagicMock()
        mock_listener2 = MagicMock()

        @on("test_type", "test_source")
        def listener1(event: Event):
            mock_listener1(event)

        @on("test_type", "test_source")
        def listener2(event: Event):
            mock_listener2(event)

        event = Event(id="1", timestamp=1, source="test_source", event_type="test_type")
        emit(event)

        mock_listener1.assert_called_once_with(event)
        mock_listener2.assert_called_once_with(event)

    def test_on_decorator_general_listeners(self):
        mock_general_listener = MagicMock()
        mock_source_listener = MagicMock()
        mock_type_listener = MagicMock()
        mock_global_listener = MagicMock()

        @on(event_type="general_type", source=None)
        def general_type_listener(event: Event):
            mock_general_listener(event)

        @on(event_type=None, source="general_source")
        def general_source_listener(event: Event):
            mock_source_listener(event)

        @on(event_type="specific_type", source="specific_source")
        def specific_listener(event: Event):
            pass # Should not be called by general event

        @on(event_type=None, source=None)
        def global_listener(event: Event):
            mock_global_listener(event)

        event = Event(id="1", timestamp=1, source="general_source", event_type="general_type")
        emit(event)

        mock_general_listener.assert_called_once_with(event)
        mock_source_listener.assert_called_once_with(event)
        mock_global_listener.assert_called_once_with(event)
        # specific_listener should not be called

    def test_emit_dispatches_to_correct_listeners(self):
        mock_specific = MagicMock()
        mock_general_type = MagicMock()
        mock_general_source = MagicMock()
        mock_global = MagicMock()

        @on("type1", "source1")
        def specific_listener(event: Event):
            mock_specific(event)

        @on("type1", None)
        def general_type_listener(event: Event):
            mock_general_type(event)

        @on(None, "source1")
        def general_source_listener(event: Event):
            mock_general_source(event)

        @on(None, None)
        def global_listener(event: Event):
            mock_global(event)

        event = Event(id="1", timestamp=1, source="source1", event_type="type1")
        emit(event)

        mock_specific.assert_called_once_with(event)
        mock_general_type.assert_called_once_with(event)
        mock_general_source.assert_called_once_with(event)
        mock_global.assert_called_once_with(event)

        # Test with a different event that should only trigger general/global listeners
        mock_specific.reset_mock()
        mock_general_type.reset_mock()
        mock_general_source.reset_mock()
        mock_global.reset_mock()

        event2 = Event(id="2", timestamp=2, source="source2", event_type="type2")
        emit(event2)

        mock_specific.assert_not_called()
        mock_general_type.assert_not_called()
        mock_general_source.assert_not_called()
        mock_global.assert_called_once_with(event2)