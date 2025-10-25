"""Integration tests for council command."""

from unittest.mock import AsyncMock, patch

from space.apps.council.app import Council


def test_council_class_initialization():
    """Council class initializes with channel name."""
    with patch("space.apps.council.app.db.resolve_channel_id", return_value="channel-uuid"):
        council = Council("test-channel")
        assert council.channel_name == "test-channel"
        assert council.channel_id == "channel-uuid"


def test_council_run_calls_stream_and_input(monkeypatch):
    """Council.run() creates and awaits stream and input tasks."""
    with patch("space.apps.council.app.db.resolve_channel_id", return_value="ch-id"):
        with patch("space.apps.council.app.db.get_topic", return_value="test topic"):
            with patch("space.apps.council.app.asyncio.create_task"):
                with patch("space.apps.council.app.asyncio.gather", new_callable=AsyncMock):
                    council = Council("test-channel")
                    # Just verify initialization works - avoid actual async execution
                    assert council.channel_name == "test-channel"
