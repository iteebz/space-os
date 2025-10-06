import pytest
from pathlib import Path
import sqlite3
import tempfile
import os

from space.apps.memory.db import ensure_schema

@pytest.fixture
def memory_db_path():
    """
    Provides a path to a temporary SQLite database for memory app tests.
    The database is initialized with the memory app's schema.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        
        # The app_root_path for ensure_schema should point to the memory app's directory
        # This path is relative to the project root, or absolute if needed.
        # For a test fixture, it's best to derive it from the test file's location.
        memory_app_root = Path(__file__).parent.parent.parent.parent / "space" / "apps" / "memory"

        with sqlite3.connect(db_path) as conn:
            ensure_schema(conn, memory_app_root)
        yield db_path
