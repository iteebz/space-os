import pytest
import sqlite3
from unittest.mock import patch

@pytest.fixture
def in_memory_db():
    """
    Provides an in-memory SQLite database connection for testing.
    Sets up the necessary schema for channels.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row # Allow accessing columns by name

    # Create channels table
    conn.execute("""
        CREATE TABLE channels (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            guide_hash TEXT,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            archived_at TIMESTAMP
        )
    """)
    # Create messages table (needed for get_participants and fetch)
    conn.execute("""
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            channel_id TEXT,
            sender TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        )
    """)
    # Create notes table (needed for fetch)
    conn.execute("""
        CREATE TABLE notes (
            id TEXT PRIMARY KEY,
            channel_id TEXT,
            author TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        )
    """)
    # Create bookmarks table (needed for fetch)
    conn.execute("""
        CREATE TABLE bookmarks (
            id TEXT PRIMARY KEY,
            agent_id TEXT,
            channel_id TEXT,
            last_seen_id TEXT,
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        )
    """)
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture(autouse=True)
def mock_db_connect(in_memory_db):
    """
    Mocks the bridge.db.connect function to return the in-memory database.
    This fixture is autoused for all tests in this directory.
    """
    with patch('space.apps.bridge.db.connect', return_value=in_memory_db):
        yield
