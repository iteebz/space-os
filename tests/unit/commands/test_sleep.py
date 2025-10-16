import time
from unittest.mock import patch

from typer.testing import CliRunner

from space.app import app
from space.models import Memory

runner = CliRunner()


def test_sleep_smoketest():
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_memories.return_value = []

        result = runner.invoke(app, ["sleep", "--as", "test-agent"])

        assert result.exit_code == 0
        assert "💀 Sleeping test-agent" in result.stdout
        assert "🧠 0 memories persisted" in result.stdout
        assert "Your last summary:" in result.stdout
        assert "  No last summary found." in result.stdout
        assert "**Before you go:**" in result.stdout
        mock_registry.get_agent_id.assert_called_once_with("test-agent")
        mock_events.identify.assert_called_once_with("test-agent", "sleep")


def test_sleep_displays_last_summary_and_guidance():
    mock_summary_id = "12345-abcde"
    mock_summary_message = "This is a test summary."
    mock_memory = Memory(
        memory_id=mock_summary_id,
        agent_id="test-agent",
        topic="summary",
        message=mock_summary_message,
        timestamp=0,
        created_at=time.time(),
    )

    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events"),
        patch("space.memory.db") as mock_memory_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_memories.return_value = [mock_memory]

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
            limit=1,
        )


def test_sleep_check_flag_prevents_persistence():
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,
    ):
        mock_registry.get_agent_id.return_value = "test-agent-id"
        mock_memory_db.get_memories.return_value = []

        result = runner.invoke(app, ["sleep", "--as", "test-agent", "--check"])

        assert result.exit_code == 0
        assert "💀 Sleeping test-agent" in result.stdout
        assert "(preview mode - changes not persisted)" in result.stdout
        mock_events.identify.assert_not_called()


def test_checkpoint_flow(test_space):
    with (
        patch("space.spawn.registry") as mock_registry,
        patch("space.events") as mock_events,
        patch("space.memory.db") as mock_memory_db,
    ):
        mock_registry.get_agent_id.return_value = "test-zealot-id"
        mock_memory_db.get_memories.return_value = []

        identity = "test-zealot"
        result = runner.invoke(app, ["sleep", "--as", identity])
        assert result.exit_code == 0

        mock_registry.get_agent_id.assert_called_once_with(identity)
        mock_events.identify.assert_called_once_with(identity, "sleep")
