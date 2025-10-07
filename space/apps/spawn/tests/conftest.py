import pytest
import sqlite3
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from pathlib import Path

from space.apps.spawn.repo import SpawnRepo
from space.os.db.migration import apply_migrations
from space.os.events.repo import EventRepo # Import EventRepo
from space.os.events import events # Import the events module

@pytest.fixture
def spawn_repo() -> SpawnRepo:
    """Provides a SpawnRepo instance with a single, persistent in-memory SQLite connection for testing."""
    conn = sqlite3.connect(":memory:") # Create a new connection for each test
    migrations_dir = Path(__file__).parent.parent / "migrations" # Get migrations dir
    apply_migrations("spawn", migrations_dir, conn) # Corrected call

    # Patch _event_repo directly
    with patch.object(events, '_event_repo', MagicMock(spec=EventRepo)) as mock_event_repo_instance:
        repo = SpawnRepo() # Instantiate without db_path

        @contextmanager
        def mock_connect(row_factory: type | None = None):
            if row_factory is not None:
                conn.row_factory = row_factory
            yield conn

        with patch.object(repo, '_connect', mock_connect):
            yield repo

    conn.close()