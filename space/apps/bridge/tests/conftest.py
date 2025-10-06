import pytest
from unittest.mock import patch
import sqlite3
from pathlib import Path
import uuid

from space.apps.bridge import db

@pytest.fixture
def mock_bridge_db_connection():
    """
    Provides a mock in-memory SQLite database connection for bridge app tests.
    Initializes the schema for each test.
    """
    unique_db_name = f"file:{uuid.uuid4()}?mode=memory&cache=shared"
    
    with patch.object(db, 'BRIDGE_DB_PATH', Path(unique_db_name)):
        # Initialize the schema for the in-memory database
        db.init()

        # Provide a connection to the in-memory database for direct assertions in tests
        conn = sqlite3.connect(unique_db_name, uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
