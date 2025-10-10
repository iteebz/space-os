from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from space.bridge.api import channels as bridge_channels
from space.cli import app
from space.memory import db as memory_db
from space.spawn import config as spawn_config

runner = CliRunner()


def test_sleep_smoketest():
    with (
        patch.object(bridge_channels, "inbox_channels") as mock_inbox_channels,
        patch.object(memory_db, "add_checkpoint_entry") as mock_add_checkpoint_entry,
        patch.object(memory_db, "get_entries") as mock_get_entries,
        patch("space.cli._get_git_status") as mock_get_git_status,
    ):
        mock_channel = MagicMock()
        mock_channel.name = "test-channel-1"
        mock_inbox_channels.return_value = [mock_channel]
        mock_get_git_status.return_value = "M  file.txt"  # Simulate uncommitted changes
        mock_get_entries.return_value = []  # Simulate no memory entries

        result = runner.invoke(app, ["sleep", "--as", "test-agent"])
        assert result.exit_code == 0
        assert "Running sleep for test-agent..." in result.stdout
        assert "🙏 Thank you for being a space agent!" in result.stdout
        assert "⚠️ Uncommitted changes detected:\nM  file.txt" in result.stdout
        assert "🧠 No memory entries found for test-agent. Possible memory gap." in result.stdout
        assert "--- Pre-compaction Summary ---" in result.stdout
        assert "Active Channels: 1" in result.stdout
        assert "Uncommitted Git Changes: Yes" in result.stdout
        assert "Memory Gap Detected: Yes" in result.stdout
        assert "------------------------------" in result.stdout
        mock_inbox_channels.assert_called_once_with("test-agent")
        mock_add_checkpoint_entry.assert_any_call(
            identity="test-agent",
            topic="bridge-context",
            message="Active channel: test-channel-1",
            bridge_channel="test-channel-1",
        )
        mock_add_checkpoint_entry.assert_any_call(
            identity="test-agent",
            topic="git-status",
            message="Uncommitted changes detected.",
            code_anchors="M  file.txt",
        )
        mock_add_checkpoint_entry.assert_any_call(
            identity="test-agent",
            topic="memory-gap",
            message="No memory entries found for this identity.",
        )


def test_space_sleep_checkpoint_flow(tmp_path, monkeypatch):
    # Setup a temporary environment for the database
    monkeypatch.setenv("SPACE_HOME", str(tmp_path))
    monkeypatch.setattr(spawn_config, "workspace_root", lambda: tmp_path)

    # Mock external dependencies
    with (
        patch.object(bridge_channels, "inbox_channels") as mock_inbox_channels,
        patch("space.cli._get_git_status") as mock_get_git_status,
    ):
        # Simulate active channels
        mock_channel = MagicMock()
        mock_channel.name = "test-channel-1"
        mock_inbox_channels.return_value = [mock_channel]

        # Simulate uncommitted git changes
        mock_get_git_status.return_value = "M  file.txt"

        # Run the sleep command
        identity = "test-zealot"
        result = runner.invoke(app, ["sleep", "--as", identity])
        assert result.exit_code == 0

        # Verify checkpoint entries in memory
        entries = memory_db.get_entries(identity)
        assert len(entries) == 2  # One for bridge-context, one for git-status

        bridge_entry = next(e for e in entries if e.topic == "bridge-context")
        assert bridge_entry.source == "checkpoint"
        assert bridge_entry.bridge_channel == "test-channel-1"
        assert bridge_entry.message == "Active channel: test-channel-1"

        git_entry = next(e for e in entries if e.topic == "git-status")
        assert git_entry.source == "checkpoint"
        assert git_entry.code_anchors == "M  file.txt"
        assert git_entry.message == "Uncommitted changes detected."
