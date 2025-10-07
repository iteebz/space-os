import pytest
import sqlite3
from unittest.mock import patch
from contextlib import contextmanager
from collections.abc import Iterator

from space.apps.memory.memory import MemoryRepo

@pytest.fixture
def memory_repo() -> MemoryRepo:
    """Provides a MemoryRepo instance with a single, persistent in-memory SQLite connection for testing."""
    # Create a single, shared in-memory database connection
    conn = sqlite3.connect(":memory:")

    # Create the schema
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE memories (
            uuid TEXT PRIMARY KEY,
            identity TEXT NOT NULL,
            topic TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    conn.commit()

    # Create a repo instance
    repo = MemoryRepo()

    # Create a context manager that will yield our single connection
    @contextmanager
    def mock_get_db_connection(row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        if row_factory is not None:
            conn.row_factory = row_factory
        yield conn

    # Patch the repo's connection method
    with patch.object(repo, 'get_db_connection', mock_get_db_connection):
        yield repo

    # Clean up the connection after the test
    conn.close()
