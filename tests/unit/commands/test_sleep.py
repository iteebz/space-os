import time
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from space.app import app
from space.models import Memory

runner = CliRunner()


def test_sleep_smoketest():
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,
        patch("space.lib.db") as mock_lib_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_memories.return_value = []  # Return empty list for smoketest
        mock_conn = MagicMock()
        mock_lib_db.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("session-123",)

        result = runner.invoke(app, ["sleep", "--as", "test-agent"])

        assert result.exit_code == 0
        assert "💀 Sleeping test-agent" in result.stdout
        assert "🧠 0 memories persisted" in result.stdout  # Updated count
        assert "Your last summary:" in result.stdout
        assert "  No last summary found." in result.stdout
        assert "**Before you go:**" in result.stdout
        mock_registry.get_agent_id.assert_called_once_with("test-agent")
        mock_events.identify.assert_called_once_with("test-agent", "sleep", "session-123")
        mock_events.end_session.assert_called_once_with("test-agent-id", "session-123")


def test_sleep_displays_last_summary_and_guidance():
    mock_summary_id = "12345-abcde"
    mock_summary_message = "This is a test summary."
    mock_memory = Memory(
        memory_id=mock_summary_id,
        agent_id="test-agent",
        topic="summary",  # Changed to 'summary'
        message=mock_summary_message,
        timestamp=0,
        created_at=time.time(),
    )

    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events"),
        patch("space.memory.db") as mock_memory_db,
        patch("space.lib.db") as mock_lib_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_memories.return_value = [mock_memory]
        mock_conn = MagicMock()
        mock_lib_db.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("session-123",)

        result = runner.invoke(app, ["sleep", "--as", "test-agent"])

        assert result.exit_code == 0
        assert "Your last summary:" in result.stdout
        assert f"  {mock_summary_message}" in result.stdout
        assert (
            f'  memory --as test-agent replace {mock_memory.memory_id} "<new summary>" '
            in result.stdout
        )
        mock_memory_db.get_memories.assert_called_with(
            "test-agent",
            topic="summary",
            limit=1,  # Changed to 'summary'
        )


def test_sleep_check_flag_prevents_persistence():
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,
        patch("space.lib.db") as mock_lib_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_memories.return_value = []  # Added mock_memory_db.get_entries here
        mock_conn = MagicMock()
        mock_lib_db.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("session-123",)

        result = runner.invoke(app, ["sleep", "--as", "test-agent", "--check"])

        assert result.exit_code == 0
        assert "💀 Sleeping test-agent" in result.stdout
        assert "(preview mode - changes not persisted)" in result.stdout
        mock_events.identify.assert_not_called()
        mock_events.end_session.assert_not_called()


def test_checkpoint_flow(test_space):
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,  # Added mock_memory_db here
        patch("space.lib.db") as mock_lib_db,
        patch("space.lib.paths") as mock_paths,
    ):
        mock_paths.space_root.return_value.exists.return_value = True
        mock_registry.get_agent_id.return_value = "test-zealot-id"
        mock_memory_db.get_memories.return_value = []
        mock_conn = MagicMock()
        mock_lib_db.connect.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchone.return_value = ("session-456",)

        identity = "test-zealot"
        result = runner.invoke(app, ["sleep", "--as", identity])
        assert result.exit_code == 0

        mock_registry.get_agent_id.assert_called_once_with(identity)
        mock_events.identify.assert_called_once_with(identity, "sleep", "session-456")
        mock_events.end_session.assert_called_once_with("test-zealot-id", "session-456")
