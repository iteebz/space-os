from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from space.apps.spawn.repo import SpawnRepo
from space.apps.spawn.models import Identity
from space.apps.spawn.cli import cli
from space.apps.spawn import add_identity, get_identity

# --- Test Data ---
TEST_IDENTITY_1 = Identity(id="agent1", type="typeA", created_at=1, updated_at=1)
TEST_IDENTITY_2 = Identity(id="agent2", type="typeB", created_at=2, updated_at=2)

# --- Tests ---

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
        """Test retrieving a non-existent identity."""
        assert spawn_repo.get_identity("non-existent") is None

class TestSpawnApi:
    @patch('space.apps.spawn.repo.SpawnRepo')
    @patch('space.os.events.track')
    def test_add_identity_no_constitution(self, mock_track: MagicMock, MockSpawnRepo: MagicMock):
        """Test that add_identity calls repo.add_identity and does not emit an event without content."""
        mock_repo_instance = MockSpawnRepo.return_value
        mock_repo_instance.add_identity.return_value = TEST_IDENTITY_1

        result = add_identity(id="agent1", type="typeA")

        mock_repo_instance.add_identity.assert_called_once_with("agent1", "typeA")
        mock_track.assert_not_called()
        assert result == TEST_IDENTITY_1

    @patch('space.apps.spawn.repo.SpawnRepo')
    @patch('space.os.events.track')
    def test_add_identity_with_constitution(self, mock_track: MagicMock, MockSpawnRepo: MagicMock):
        """Test that add_identity emits an event when initial constitution content is provided."""
        mock_repo_instance = MockSpawnRepo.return_value
        mock_repo_instance.add_identity.return_value = TEST_IDENTITY_1

        result = add_identity(id="agent1", type="typeA", initial_constitution_content="some content")

        mock_repo_instance.add_identity.assert_called_once_with("agent1", "typeA")
        mock_track.assert_called_once_with(
            source="spawn",
            event_type="identity.created",
            identity="agent1",
            data={
                "identity_id": "agent1",
                "identity_type": "typeA",
                "initial_constitution_content": "some content",
            },
        )
        assert result == TEST_IDENTITY_1

    @patch('space.apps.spawn.repo.SpawnRepo')
    def test_get_identity(self, MockSpawnRepo: MagicMock):
        """Test that get_identity calls repo.get_identity."""
        mock_repo_instance = MockSpawnRepo.return_value
        mock_repo_instance.get_identity.return_value = TEST_IDENTITY_1

        result = get_identity(id="agent1")

        mock_repo_instance.get_identity.assert_called_once_with("agent1")
        assert result == TEST_IDENTITY_1

class TestSpawnCli:
    def test_add_identity_command(self):
        """Test the 'add-identity' CLI command without initial constitution content."""
        runner = CliRunner()
        with patch('space.apps.spawn.cli.api_add_identity') as mock_add_identity:
            mock_add_identity.return_value = TEST_IDENTITY_1
            result = runner.invoke(cli, ["add-identity", "agent1", "typeA"])
            assert result.exit_code == 0
            assert "Identity 'agent1' (typeA) added." in result.output
            mock_add_identity.assert_called_once_with("agent1", "typeA", None)

    def test_add_identity_command_with_constitution(self):
        """Test the 'add-identity' CLI command with initial constitution content."""
        runner = CliRunner()
        with patch('space.apps.spawn.cli.api_add_identity') as mock_add_identity:
            mock_add_identity.return_value = TEST_IDENTITY_1
            result = runner.invoke(cli, ["add-identity", "agent1", "typeA", "--initial-constitution-content", "some content"])
            assert result.exit_code == 0
            assert "Identity 'agent1' (typeA) added." in result.output
            assert "Initial constitution content provided. An event has been emitted for registration." in result.output
            mock_add_identity.assert_called_once_with("agent1", "typeA", "some content")

    def test_get_identity_command(self):
        """Test the 'get-identity' CLI command."""
        runner = CliRunner()
        with patch('space.apps.spawn.cli.api_get_identity') as mock_get_identity:
            mock_get_identity.return_value = TEST_IDENTITY_1
            result = runner.invoke(cli, ["get-identity", "agent1"])
            assert result.exit_code == 0
            assert "Identity ID: agent1" in result.output
            assert "Type: typeA" in result.output
            mock_get_identity.assert_called_once_with("agent1")

    def test_get_identity_command_not_found(self):
        """Test the 'get-identity' CLI command when identity is not found."""
        runner = CliRunner()
        with patch('space.apps.spawn.cli.api_get_identity') as mock_get_identity:
            mock_get_identity.return_value = None
            result = runner.invoke(cli, ["get-identity", "non-existent"])
            assert result.exit_code == 0
            assert "Identity with ID 'non-existent' not found." in result.output
            mock_get_identity.assert_called_once_with("non-existent")
