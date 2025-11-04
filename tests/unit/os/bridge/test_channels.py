"""Bridge channels API contract tests."""

import pytest

from space.os import bridge
from tests.conftest import make_mock_row


def test_create_channel(mock_db):
    result = bridge.create_channel("general", "topic")
    assert result.name == "general"
    assert mock_db.execute.called


def test_create_channel_requires_name(mock_db):
    with pytest.raises(ValueError, match="name is required"):
        bridge.create_channel("")


def test_rename_channel(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"channel_id": "ch-1"})
    assert bridge.rename_channel("old", "new") is True


def test_rename_channel_missing(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    assert bridge.rename_channel("old", "new") is False


def test_archive_channel(mock_db):
    mock_db.execute.return_value.rowcount = 1
    bridge.archive_channel("general")
    assert mock_db.execute.called


def test_archive_channel_missing(mock_db):
    mock_db.execute.return_value.rowcount = 0
    with pytest.raises(ValueError, match="not found"):
        bridge.archive_channel("missing")


def test_toggle_pin_channel(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"pinned_at": None})
    assert bridge.toggle_pin_channel("general") is True

    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"pinned_at": "2024-01-01"})
    assert bridge.toggle_pin_channel("general") is False


def test_delete_channel(mock_db):
    mock_db.execute.return_value.fetchone.return_value = make_mock_row({"channel_id": "ch-1"})
    bridge.delete_channel("general")
    calls = [call[0][0] for call in mock_db.execute.call_args_list]
    assert any("DELETE FROM channels" in call for call in calls)


def test_delete_channel_missing(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError, match="not found"):
        bridge.delete_channel("missing")


def test_list_channels(mock_db):
    mock_row = make_mock_row(
        {
            "channel_id": "ch-1",
            "name": "general",
            "topic": None,
            "created_at": "2024-01-01",
            "archived_at": None,
            "message_count": 10,
            "last_activity": "2024-01-02",
            "unread_count": 0,
        }
    )
    mock_db.execute.return_value.fetchall.return_value = [mock_row]
    result = bridge.list_channels()
    assert len(result) == 1
    args = mock_db.execute.call_args[0][0]
    assert "archived_at IS NULL" in args


def test_get_channel(mock_db):
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

    mock_db.execute.return_value.fetchone.return_value = None
    assert bridge.get_channel("missing") is None
