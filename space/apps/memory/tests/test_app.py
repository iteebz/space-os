from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import sqlite3
from contextlib import contextmanager

from space.apps.memory.memory import MemoryRepo, Memory
from space.apps.memory.cli import cli
from space.apps.memory import memory

# --- Test Data ---
TEST_MEMORY_1 = Memory(uuid="uuid-1", identity="test", topic="test", message="message 1", created_at=1)
TEST_MEMORY_2 = Memory(uuid="uuid-2", identity="test", topic="test", message="message 2", created_at=2)

# --- Tests ---

class TestMemoryRepo:
    def test_add_and_get_all(self, memory_repo: MemoryRepo):
        """Test adding a memory and retrieving all memories from the repo."""
        assert memory_repo.get_all() == []

        with patch('space.apps.memory.memory.uuid7', return_value="test-uuid-1"):
            memory_repo.add(identity="test", topic="test", message="test message")

        memories = memory_repo.get_all()
        assert len(memories) == 1
        memory = memories[0]
        assert memory.uuid == "test-uuid-1"
        assert memory.identity == "test"
        assert memory.topic == "test"
        assert memory.message == "test message"

class TestMemoryPublicAPI:
    @patch('space.apps.memory.memory.repo')
    def test_add_memory(self, mock_repo: MagicMock):
        """Test that the add_memory API function calls the repo's add method."""
        memory.add_memory(identity="test", topic="test", message="test message")
        mock_repo.add.assert_called_once_with("test", "test", "test message")

    @patch('space.apps.memory.memory.repo')
    def test_get_all_memories(self, mock_repo: MagicMock):
        """Test that the get_all_memories API function calls the repo's get_all method."""
        mock_repo.get_all.return_value = [TEST_MEMORY_1, TEST_MEMORY_2]
        result = memory.get_all_memories()
        mock_repo.get_all.assert_called_once()
        assert result == [TEST_MEMORY_1, TEST_MEMORY_2]

class TestMemoryCli:
    _db_conn: sqlite3.Connection
    _patcher: patch

    def setup_method(self):
        # Create a single, shared in-memory database connection for CLI tests
        self._db_conn = sqlite3.connect(":memory:")
        cursor = self._db_conn.cursor()
        cursor.execute("""
            CREATE TABLE memories (
                uuid TEXT PRIMARY KEY,
                identity TEXT NOT NULL,
                topic TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        self._db_conn.commit()

        # Create a context manager that will yield our single connection
        @contextmanager
        def mock_get_db_connection(*args, **kwargs):
            yield self._db_conn

        # Patch the global repo's connection method
        self._patcher = patch.object(memory.repo, 'get_db_connection', mock_get_db_connection)
        self._patcher.start()

    def teardown_method(self):
        self._patcher.stop()
        self._db_conn.close()

    def test_list_command(self):
        """Test the 'list' CLI command."""
        runner = CliRunner()
        with patch('space.apps.memory.cli.get_all_memories') as mock_get_all:
            mock_get_all.return_value = [TEST_MEMORY_1, TEST_MEMORY_2]
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "message 1" in result.output
            assert "message 2" in result.output

    def test_add_command(self):
        """Test the 'add' CLI command."""
        runner = CliRunner()
        with patch('space.apps.memory.cli.add_memory') as mock_add:
            result = runner.invoke(cli, ["add", "--identity", "test", "--topic", "cli", "A message from CLI"])
            assert result.exit_code == 0
            assert "Memory added." in result.output
            mock_add.assert_called_once_with("test", "cli", "A message from CLI")