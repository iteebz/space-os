from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call
import pytest

from space.apps.spawn.models import Identity
from space.apps.spawn.repo import SpawnRepo
from space.apps.spawn import add_identity, get_identity
from space.cli import cli
from click.testing import CliRunner # Import CliRunner

# Define a test identity for consistent use
TEST_IDENTITY_1 = Identity(
    id="agent1",
    type="typeA",
    created_at=int(datetime.now(timezone.utc).timestamp()),
    updated_at=int(datetime.now(timezone.utc).timestamp()),
)

class TestSpawnRepo:
    def test_add_and_get_identity(self, spawn_repo: SpawnRepo):
        """Test adding an identity and retrieving it from the repo."""
        assert spawn_repo.get_identity("agent1") is None

        identity = spawn_repo.add_identity(id="agent1", type="typeA")
        assert identity.id == "agent1"
        assert identity.type == "typeA"

        retrieved_identity = spawn_repo.get_identity("agent1")
        assert retrieved_identity == identity

    def test_get_non_existent_identity(self, spawn_repo: SpawnRepo):
        """Test retrieving a non-existent identity returns None."""
        assert spawn_repo.get_identity("non-existent") is None

class TestSpawnApi:
    @patch('space.apps.spawn.repo') # Patch the instance
    @patch('space.os.events.track')
    @patch('space.os.lib.uuid7.uuid7', return_value="mock-uuid-1") # Patch here
    def test_add_identity_no_constitution(self, mock_uuid7: MagicMock, mock_track: MagicMock, mock_spawn_repo_instance: MagicMock):
        """Test that add_identity calls repo.add_identity and emits only identity.created event."""
        mock_spawn_repo_instance.add_identity.return_value = TEST_IDENTITY_1

        result = add_identity(id="agent1", type="typeA")

        mock_spawn_repo_instance.add_identity.assert_called_once_with("agent1", "typeA")
        mock_track.assert_called_once_with(
            source="spawn",
            event_type="identity.created",
            identity="agent1",
            data={
                "identity_id": "agent1",
                "identity_type": "typeA",
                "initial_constitution_content": None
            }
        )
        assert result == TEST_IDENTITY_1

    @patch('space.apps.spawn.repo') # Patch the instance
    @patch('space.os.events.track')
    @patch('space.os.lib.uuid7.uuid7', side_effect=["mock-uuid-1", "mock-uuid-2"]) # Patch here with side_effect
    def test_add_identity_with_constitution(self, mock_uuid7: MagicMock, mock_track: MagicMock, mock_spawn_repo_instance: MagicMock):
        """Test that add_identity emits both identity.created and constitution_created events."""
        mock_spawn_repo_instance.add_identity.return_value = TEST_IDENTITY_1

        result = add_identity(id="agent1", type="typeA", initial_constitution_content="some content")

        mock_spawn_repo_instance.add_identity.assert_called_once_with("agent1", "typeA")
        mock_track.assert_has_calls([
            call(
                source="spawn",
                event_type="identity.created",
                identity="agent1",
                data={
                    "identity_id": "agent1",
                    "identity_type": "typeA",
                    "initial_constitution_content": "some content"
                }
            ),
            call(
                source="spawn",
                event_type="constitution_created",
                identity="agent1",
                data={
                    "constitution_id": "mock-uuid-1", # Use the first uuid from side_effect
                    "content": "some content"
                }
            )
        ], any_order=True)
        assert mock_track.call_count == 2
        assert result == TEST_IDENTITY_1

    @patch('space.apps.spawn.repo') # Patch the instance
    def test_get_identity(self, mock_spawn_repo_instance: MagicMock):
        """Test that get_identity calls repo.get_identity."""
        mock_spawn_repo_instance.get_identity.return_value = TEST_IDENTITY_1

        result = get_identity(id="agent1")

        mock_spawn_repo_instance.get_identity.assert_called_once_with("agent1")
        assert result == TEST_IDENTITY_1

    @patch('space.apps.spawn.repo') # Patch the instance
    def test_get_identity_not_found(self, mock_spawn_repo_instance: MagicMock):
        """Test that get_identity returns None if identity is not found."""
        mock_spawn_repo_instance.get_identity.return_value = None

        result = get_identity(id="non-existent")

        mock_spawn_repo_instance.get_identity.assert_called_once_with("non-existent")
        assert result is None

class TestSpawnCli:
    @patch('space.apps.spawn.repo') # Patch the instance
    @patch('space.os.events.track')
    @patch('space.os.lib.uuid7.uuid7', return_value="mock-uuid-1") # Patch here
    def test_add_identity_command(self, mock_uuid7: MagicMock, mock_track: MagicMock, mock_spawn_repo_instance: MagicMock, capsys):
        """Test the 'spawn add-identity' CLI command."""
        mock_spawn_repo_instance.add_identity.return_value = TEST_IDENTITY_1

        runner = CliRunner()
        result = runner.invoke(cli, ["spawn", "add-identity", "--id", "agent1", "--type", "typeA"])

        assert result.exit_code == 0
        mock_spawn_repo_instance.add_identity.assert_called_once_with("agent1", "typeA")
        mock_track.assert_called_once_with(
            source="spawn",
            event_type="identity.created",
            identity="agent1",
            data={
                "identity_id": "agent1",
                "identity_type": "typeA",
                "initial_constitution_content": None
            }
        )
        assert "Identity agent1 (typeA) created." in result.output

    @patch('space.apps.spawn.repo') # Patch the instance
    @patch('space.os.events.track')
    @patch('space.os.lib.uuid7.uuid7', side_effect=["mock-uuid-1", "mock-uuid-2"]) # Patch here with side_effect
    def test_add_identity_command_with_constitution(self, mock_uuid7: MagicMock, mock_track: MagicMock, mock_spawn_repo_instance: MagicMock, capsys):
        """Test the 'spawn add-identity' CLI command with initial constitution content."""
        mock_spawn_repo_instance.add_identity.return_value = TEST_IDENTITY_1

        runner = CliRunner()
        result = runner.invoke(cli, [
            "spawn", "add-identity", "--id", "agent1", "--type", "typeA",
            "--initial-constitution-content", "some content"
        ])

        assert result.exit_code == 0
        mock_spawn_repo_instance.add_identity.assert_called_once_with("agent1", "typeA")
        mock_track.assert_has_calls([
            call(
                source="spawn",
                event_type="identity.created",
                identity="agent1",
                data={
                    "identity_id": "agent1",
                    "identity_type": "typeA",
                    "initial_constitution_content": "some content"
                }
            ),
            call(
                source="spawn",
                event_type="constitution_created",
                identity="agent1",
                data={
                    "constitution_id": "mock-uuid-1", # Use the first uuid from side_effect
                    "content": "some content"
                }
            )
        ], any_order=True)
        assert mock_track.call_count == 2
        assert "Identity agent1 (typeA) created with initial constitution." in result.output

    @patch('space.apps.spawn.repo') # Patch the instance
    def test_get_identity_command(self, mock_spawn_repo_instance: MagicMock, capsys):
        """Test the 'spawn get-identity' CLI command."""
        mock_spawn_repo_instance.get_identity.return_value = TEST_IDENTITY_1

        runner = CliRunner()
        result = runner.invoke(cli, ["spawn", "get-identity", "--id", "agent1"])

        assert result.exit_code == 0
        mock_spawn_repo_instance.get_identity.assert_called_once_with("agent1")
        assert "ID: agent1" in result.output
        assert "Type: typeA" in result.output

    @patch('space.apps.spawn.repo') # Patch the instance
    def test_get_identity_command_not_found(self, mock_spawn_repo_instance: MagicMock, capsys):
        """Test the 'spawn get-identity' CLI command for a non-existent identity."""
        mock_spawn_repo_instance.get_identity.return_value = None

        runner = CliRunner()
        result = runner.invoke(cli, ["spawn", "get-identity", "--id", "non-existent"])

        assert result.exit_code == 0
        mock_spawn_repo_instance.get_identity.assert_called_once_with("non-existent")
        assert "Identity 'non-existent' not found." in result.output