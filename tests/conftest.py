"""Pytest configuration for agent-space tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db(monkeypatch):
    """Use temporary database for tests, ensuring true isolation."""
    from space import events
    from space.lib import context_db, storage

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_space_dir = Path(tmpdir)
        monkeypatch.setattr(storage, "SPACE_DIR", temp_space_dir)

        # Ensure a clean slate for migration logic
        monkeypatch.setattr(context_db, "_MIGRATED", False)

        # Setup context_db
        context_db_path = temp_space_dir / "context.db"
        context_db.ensure()

        # Setup events_db
        events_db_path = temp_space_dir / "events.db"
        original_events_db_path = events.DB_PATH
        events.DB_PATH = events_db_path
        events.init_db()

        yield context_db_path

        # Teardown events_db
        events.DB_PATH = original_events_db_path
