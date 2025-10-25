"""Integration tests for council command."""

from unittest.mock import patch

from space.apps.council.app import Council


def test_council_class_initialization():
    """Council class initializes with channel name."""
    with patch("space.apps.council.app.db.resolve_channel_id", return_value="channel-uuid"):
        council = Council("test-channel")
        assert council.channel_name == "test-channel"
        assert council.channel_id == "channel-uuid"


def test_council_init_resolves_channel():
    """Resolve channel_id during initialization."""
    with patch("space.apps.council.app.db.resolve_channel_id", return_value="ch-id"):
        with patch("space.apps.council.app.asyncio.create_task"):
            council = Council("test-channel")
            assert council.channel_name == "test-channel"
            assert council.channel_id == "ch-id"
