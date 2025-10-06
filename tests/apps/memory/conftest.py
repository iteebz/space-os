import pytest
from pathlib import Path
import sqlite3
import tempfile
import os
from unittest.mock import patch

from space.apps.memory.app import memory_app
from space.apps.memory.repo import MemoryRepo

@pytest.fixture
def memory_db_path():
    """
    Provides a path to a temporary SQLite database for memory app tests.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        yield db_path

@pytest.fixture(autouse=True)
def mock_memory_app_db_path(memory_db_path):
    """
    Patches the memory_app's db_path to use a temporary database for tests
    and re-instantiates the MemoryRepository with this temporary path.
    """
    original_db_path = memory_app.db_path
    original_repositories = memory_app._repositories.copy()

    # Patch the db_path
    with patch.object(memory_app, '_db_path', memory_db_path):
        # Re-instantiate the repository with the temporary db_path
        # The MemoryRepository constructor now only takes app_name
        memory_app._repositories["memory"] = MemoryRepo("memory")
        yield

    # Restore original db_path and repositories after tests
    memory_app._db_path = original_db_path
    memory_app._repositories = original_repositories
