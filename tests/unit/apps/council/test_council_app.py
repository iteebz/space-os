"""Tests for Council class."""

from unittest.mock import patch

import pytest

from space.apps.council.app import Council


@pytest.fixture
def mock_channel():
    """Mock channel data."""
    return {
        "channel_name": "test-channel",
        "channel_id": "ch-123",
    }


@pytest.fixture
def council_instance(mock_channel):
    """Create a Council instance with mocked API."""
    with patch("space.apps.council.app.db.resolve_channel_id") as mock_resolve:
        mock_resolve.return_value = mock_channel["channel_id"]
        return Council(mock_channel["channel_name"])


def test_initialization(council_instance, mock_channel):
    """Council initializes with channel."""
    assert council_instance.channel_name == mock_channel["channel_name"]
    assert council_instance.channel_id == mock_channel["channel_id"]
    assert council_instance.running is True
    assert council_instance.last_msg_id is None
    assert len(council_instance.sent_msg_ids) == 0


def test_print_error_writes_stderr(council_instance):
    """_print_error writes to stderr."""
    output = []

    def capture_print(*args, **kwargs):
        output.append((args, kwargs))

    import sys

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_error("Test error")

    assert len(output) == 1
    assert "Test error" in output[0][0][0]
    assert output[0][1].get("file") == sys.stderr
