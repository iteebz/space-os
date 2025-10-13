from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_sleep_smoketest():
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,
        patch("space.lib.db") as mock_lib_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_entries.return_value = [1, 2, 3]
        mock_conn = MagicMock()
        mock_lib_db.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("session-123",)

        result = runner.invoke(app, ["sleep", "--as", "test-agent"])

        assert result.exit_code == 0
        assert "💀 Sleeping test-agent" in result.stdout
        assert "🧠 3 memories persisted" in result.stdout
        assert "**Before you go:**" in result.stdout
        mock_registry.get_agent_id.assert_called_once_with("test-agent")
        mock_events.identify.assert_called_once_with("test-agent", "sleep", "session-123")
        mock_events.end_session.assert_called_once_with("test-agent-id", "session-123")


def test_checkpoint_flow(test_space):
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db"),
        patch("space.lib.db") as mock_lib_db,
        patch("space.lib.paths") as mock_paths,
    ):
        mock_paths.space_root.return_value.exists.return_value = True
        mock_registry.get_agent_id.return_value = "test-zealot-id"
        mock_conn = MagicMock()
        mock_lib_db.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("session-456",)

        identity = "test-zealot"
        result = runner.invoke(app, ["sleep", "--as", identity])
        assert result.exit_code == 0

        mock_registry.get_agent_id.assert_called_once_with(identity)
        mock_events.identify.assert_called_once_with(identity, "sleep", "session-456")
        mock_events.end_session.assert_called_once_with("test-zealot-id", "session-456")
