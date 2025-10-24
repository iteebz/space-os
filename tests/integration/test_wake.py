import time
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from space.cli import app
from space.os.models import Channel

runner = CliRunner()


def test_wake_new_identity_spawn_count_zero(test_space):
    with (
        patch("space.os.events.identify"),
        patch("space.os.events.get_sleep_count", return_value=0),
        patch("space.os.events.get_wake_count", return_value=1),
        patch("space.os.events.get_last_sleep_time", return_value=time.time()),  # Mock with float
        patch("space.os.knowledge.db.list_all", return_value=[]),  # Mock knowledge dependency
        patch("space.os.lib.chats.sync"),
    ):
        result = runner.invoke(app, ["wake", "--as", "new-agent"])
        assert result.exit_code == 0
        assert "Waking up new-agent" in result.stdout
        assert "Spawn #0" in result.stdout


def test_wake_existing_identity_spawn_count(test_space):
    with (
        patch("space.os.events.identify"),
        patch("space.os.events.get_sleep_count", return_value=5),
        patch("space.os.events.get_wake_count", return_value=7),
        patch(
            "space.os.events.get_last_sleep_time", return_value=time.time() - 3600 * 24 * 2
        ),  # Mock with float (2 days ago)
        patch("space.os.bridge.api.channels.inbox_channels", return_value=[]),
        patch("space.os.knowledge.db.list_all", return_value=[]),  # Mock knowledge dependency
        patch("space.os.memory.db.get_memories", return_value=[]),  # Mock memory dependency
        patch("space.os.lib.chats.sync"),
    ):
        result = runner.invoke(app, ["wake", "--as", "existing-agent"])
        assert result.exit_code == 0
        assert "Spawn #5" in result.stdout
        assert (
            "Last sleep" in result.stdout
        )  # Check for presence, not exact string due to time diff


def test_command_unread_messages(test_space):
    mock_channel1 = MagicMock(spec=Channel)
    mock_channel1.name = "channel-alpha"
    mock_channel1.unread_count = 2
    mock_channel1.last_activity = "2025-10-14T10:00:00"

    mock_channel2 = MagicMock(spec=Channel)
    mock_channel2.name = "channel-beta"
    mock_channel2.unread_count = 1
    mock_channel2.last_activity = "2025-10-14T11:00:00"

    with (
        patch("space.os.events.identify"),
        patch("space.os.events.get_sleep_count", return_value=1),
        patch("space.os.events.get_wake_count", return_value=3),
        patch(
            "space.os.events.get_last_sleep_time", return_value=time.time() - 3600 * 24
        ),  # Mock with float (1 day ago)
        patch(
            "space.os.bridge.api.channels.inbox_channels",
            return_value=[mock_channel1, mock_channel2],
        ),
        patch("space.os.knowledge.db.list_all", return_value=[]),  # Mock knowledge dependency
        patch("space.os.memory.db.get_memories", return_value=[]),  # Mock memory dependency
        patch("space.os.lib.chats.sync"),
    ):
        result = runner.invoke(app, ["wake", "--as", "test-agent"])
        assert result.exit_code == 0
        assert "Waking up test-agent" in result.stdout
        assert "📬 3 messages in 2 channels:" in result.stdout
        assert "  #channel-alpha (2 unread)" in result.stdout
        assert "  #channel-beta (1 unread)" in result.stdout
        assert "bridge recv <channel> --as test-agent" in result.stdout


def test_wake_prioritizes_space_feedback(test_space):
    mock_feedback_channel = MagicMock(spec=Channel)
    mock_feedback_channel.name = "space-feedback"
    mock_feedback_channel.unread_count = 5
    mock_feedback_channel.last_activity = "2025-10-14T12:00:00"

    mock_other_channel = MagicMock(spec=Channel)
    mock_other_channel.name = "other-channel"
    mock_other_channel.unread_count = 10
    mock_other_channel.last_activity = "2025-10-14T13:00:00"

    with (
        patch("space.os.events.identify"),
        patch("space.os.events.get_sleep_count", return_value=1),
        patch("space.os.events.get_wake_count", return_value=2),
        patch(
            "space.os.events.get_last_sleep_time", return_value=time.time() - 3600 * 24
        ),  # Mock with float (1 day ago)
        patch(
            "space.os.bridge.api.channels.inbox_channels",
            return_value=[mock_other_channel, mock_feedback_channel],
        ),
        patch("space.os.knowledge.db.list_all", return_value=[]),  # Mock knowledge dependency
        patch("space.os.lib.chats.sync"),
    ):
        result = runner.invoke(app, ["wake", "--as", "test-agent"])
        assert result.exit_code == 0
        assert "#space-feedback (5 unread) ← START HERE" in result.stdout
        assert "#other-channel (10 unread)" in result.stdout  # Ensure other channel is still listed


def test_show_wake_summary_uses_prompt_constants(test_space):
    from space.commands import wake
    from space.os.lib.display import show_wake_summary
    from space.os.spawn import db as spawn_db

    identity = "test-agent"
    spawn_db.ensure_agent(identity)
    spawn_db.set_self_description(identity, "A test agent for prompt constants.")

    # Mock dependencies for show_wake_summary
    with (
        patch("space.os.events.get_last_sleep_time", return_value=time.time() - 3600),
        patch("space.os.memory.db.get_memories", return_value=[]),
        patch("space.os.memory.db.get_core_entries", return_value=[]),
        patch("space.os.memory.db.get_recent_entries", return_value=[]),
        patch("space.os.bridge.db.get_sender_history", return_value=[]),
        patch("space.os.bridge.api.channels.inbox_channels", return_value=[]),
        patch("space.os.knowledge.db.list_all", return_value=[]),
    ):
        # Capture stdout
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            show_wake_summary(
                identity=identity, quiet_output=False, spawn_count=1, wakes_this_spawn=3
            )
        output = f.getvalue()

        # Assert that the output contains the expected constants from wake.py
        assert wake.IDENTITY_HEADER.format(identity=identity) in output
        assert (
            wake.SELF_DESCRIPTION.format(description="A test agent for prompt constants.") in output
        )
        assert "Spawn #1" in output  # This is part of SPAWN_STATUS
