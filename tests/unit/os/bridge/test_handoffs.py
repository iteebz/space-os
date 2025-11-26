"""Handoffs API unit tests."""

import pytest

from space.os.bridge.api import handoffs
from tests.conftest import make_mock_row


def test_create_handoff_requires_valid_channel(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    with pytest.raises(ValueError, match="not found"):
        handoffs.create_handoff("missing", "from", "to", "summary")


def test_get_handoff_by_id(mock_db):
    mock_row = make_mock_row(
        {
            "handoff_id": "h-123",
            "channel_id": "ch-1",
            "from_agent": "a-1",
            "to_agent": "a-2",
            "summary": "test",
            "message_id": "m-1",
            "status": "pending",
            "created_at": "2024-01-01",
            "closed_at": None,
        }
    )
    mock_db.execute.return_value.fetchone.return_value = mock_row
    result = handoffs.get_handoff("h-123")
    assert result.handoff_id == "h-123"
    assert result.status == "pending"


def test_get_handoff_not_found(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    assert handoffs.get_handoff("missing") is None


def test_close_handoff_not_found(mock_db):
    mock_db.execute.return_value.fetchone.return_value = None
    assert handoffs.close_handoff("missing") is None


def test_list_pending_empty(mock_db):
    mock_db.execute.return_value.fetchall.return_value = []
    result = handoffs.list_pending()
    assert result == []
