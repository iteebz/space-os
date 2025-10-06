"""Memory contract tests - CRUD operations for agent notebook."""

from pathlib import Path

import pytest

from space.apps.memory.db import add_entry, clear_entries, delete_entry, edit_entry, get_entries


@pytest.fixture
def temp_db(monkeypatch):
    """Use a unique in-memory database for each test."""
    from space.context import db as context_db
    from space.lib import db_utils as utils

    # Patch storage.database_path to return a unique in-memory path for each test
    # This ensures context_db.ensure() and context_db.connect() use the in-memory db
    monkeypatch.setattr(utils, "database_path", lambda name: Path(":memory:"))

    # Ensure the schema is applied to the in-memory database
    context_db.ensure()
    yield
    # No explicit teardown needed for in-memory db


def test_write_entry(temp_db):
    """Agent writes memory entry."""
    add_entry("zealot-1", "space-dev", "Test entry")
    entries = get_entries("zealot-1", "space-dev")
    assert len(entries) == 1
    assert entries[0].message == "Test entry"
    assert entries[0].topic == "space-dev"
    assert entries[0].identity == "zealot-1"


def test_read_by_topic(temp_db):
    """Agent reads specific topic."""
    add_entry("zealot-1", "protoss", "Protoss work")
    add_entry("zealot-1", "space-dev", "Space work")

    entries = get_entries("zealot-1", "protoss")
    assert len(entries) == 1
    assert entries[0].message == "Protoss work"


def test_read_all_topics(temp_db):
    """Agent reads all topics."""
    add_entry("zealot-1", "protoss", "Protoss work")
    add_entry("zealot-1", "space-dev", "Space work")

    entries = get_entries("zealot-1", None)
    assert len(entries) == 2


def test_edit_entry(temp_db):
    """Agent edits existing entry."""
    add_entry("zealot-1", "space-dev", "Original")
    entries = get_entries("zealot-1", "space-dev")
    entry_uuid = entries[0].uuid

    edit_entry(entry_uuid, "Updated message")

    entries = get_entries("zealot-1", "space-dev")
    assert len(entries) == 1
    assert entries[0].message == "Updated message"


def test_delete_entry(temp_db):
    """Agent deletes specific entry."""
    add_entry("zealot-1", "space-dev", "Entry 1")
    add_entry("zealot-1", "space-dev", "Entry 2")

    entries = get_entries("zealot-1", "space-dev")
    assert len(entries) == 2

    delete_entry(entries[0].uuid)

    entries = get_entries("zealot-1", "space-dev")
    assert len(entries) == 1
    assert entries[0].message == "Entry 2"


def test_clear_topic(temp_db):
    """Agent clears entire topic."""
    add_entry("zealot-1", "space-dev", "Entry 1")
    add_entry("zealot-1", "space-dev", "Entry 2")
    add_entry("zealot-1", "protoss", "Keep this")

    clear_entries("zealot-1", "space-dev")

    space_entries = get_entries("zealot-1", "space-dev")
    assert len(space_entries) == 0

    protoss_entries = get_entries("zealot-1", "protoss")
    assert len(protoss_entries) == 1


def test_clear_all_topics(temp_db):
    """Agent clears all their memory."""
    add_entry("zealot-1", "space-dev", "Entry 1")
    add_entry("zealot-1", "protoss", "Entry 2")

    clear_entries("zealot-1", None)

    entries = get_entries("zealot-1", None)
    assert len(entries) == 0


def test_identity_isolation(temp_db):
    """Memory is identity-scoped."""
    add_entry("zealot-1", "space-dev", "Zealot work")
    add_entry("harbinger-1", "space-dev", "Harbinger work")

    zealot_entries = get_entries("zealot-1", "space-dev")
    assert len(zealot_entries) == 1
    assert zealot_entries[0].message == "Zealot work"

    harbinger_entries = get_entries("harbinger-1", "space-dev")
    assert len(harbinger_entries) == 1
    assert harbinger_entries[0].message == "Harbinger work"
