"""Bridge channels API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.core import bridge


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def mock_db():
    conn = MagicMock()
    with patch("space.lib.store.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = conn
        mock_ensure.return_value.__exit__.return_value = None
        yield conn


def test_create_channel_inserts_record(mock_db):
    bridge.create_channel("general", "topic")
    assert mock_db.execute.called


def test_create_channel_requires_name(mock_db):
    with pytest.raises(ValueError, match="name is required"):
        bridge.create_channel("")


def test_create_channel_returns_channel(mock_db):
    result = bridge.create_channel("general")
    assert result.name == "general"


def test_resolve_channel_finds_existing(mock_db):
    mock_row = make_mock_row(
        {
            "channel_id": "ch-1",
            "name": "general",
            "topic": None,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    mock_db.execute.return_value.fetchall.return_value = []

    result = bridge.resolve_channel("general")
    assert result.channel_id == "ch-1"


def test_resolve_channel_creates_missing(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    bridge.resolve_channel("newch")
    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("INSERT INTO channels" in call for call in calls)


def test_rename_channel_updates(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"channel_id": "ch-1"})
    assert bridge.rename_channel("old", "new") is True


def test_rename_channel_missing_returns_false(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    assert bridge.rename_channel("old", "new") is False


def test_archive_channel_updates(mock_db):
    mock_db.execute.return_value.rowcount = 1
    bridge.archive_channel("general")
    assert mock_db.execute.called


def test_archive_channel_missing_raises(mock_db):
    mock_db.execute.return_value.rowcount = 0
    with pytest.raises(ValueError, match="not found"):
        bridge.archive_channel("missing")


def test_pin_channel_updates(mock_db):
    mock_db.execute.return_value.rowcount = 1
    bridge.pin_channel("general")
    assert mock_db.execute.called


def test_unpin_channel_updates(mock_db):
    mock_db.execute.return_value.rowcount = 1
    bridge.unpin_channel("general")
    assert mock_db.execute.called


def test_delete_channel_hard_deletes(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"channel_id": "ch-1"})
    bridge.delete_channel("general")
    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("DELETE FROM channels" in call for call in calls)


def test_delete_channel_missing_raises(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError, match="not found"):
        bridge.delete_channel("missing")


def test_list_channels_returns_list(mock_db):
    mock_row = make_mock_row(
        {
            "channel_id": "ch-1",
            "name": "general",
            "topic": None,
            "created_at": "2024-01-01",
            "archived_at": None,
            "message_count": 10,
            "last_activity": "2024-01-02",
            "notes_count": 2,
            "unread_count": 0,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    result = bridge.list_channels()
    assert len(result) == 1


def test_list_channels_excludes_archived(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    bridge.list_channels()
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" in args


def test_get_channel_returns_channel(mock_db):
    mock_row = make_mock_row(
        {
            "channel_id": "ch-1",
            "name": "general",
            "topic": None,
            "created_at": "2024-01-01",
            "archived_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    mock_db.execute.return_value.fetchall.return_value = []
    result = bridge.get_channel("ch-1")
    assert result.channel_id == "ch-1"


def test_get_channel_missing_returns_none(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    result = bridge.get_channel("missing")
    assert result is None


def test_export_channel_returns_export(mock_db):
    with patch("space.core.bridge.api.channels.get_channel") as mock_get:
        mock_channel = MagicMock(channel_id="ch-1", name="general", topic=None, members=["a-1"])
        mock_get.return_value = mock_channel
        with patch("space.core.bridge.api.channels.messaging.get_messages") as mock_msgs:
            mock_msgs.return_value = []
            with patch("space.core.bridge.api.channels.notes.get_notes") as mock_notes:
                mock_notes.return_value = []
                result = bridge.export_channel("ch-1")
                assert result.channel_id == "ch-1"


def test_export_channel_missing_raises(mock_db):
    with patch("space.core.bridge.api.channels.get_channel") as mock_get:
        mock_get.return_value = None
        with pytest.raises(ValueError, match="not found"):
            bridge.export_channel("missing")
