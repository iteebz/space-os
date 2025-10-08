"""Memory contract tests - CRUD operations for agent notebook."""

from space.memory import storage


def test_write_entry(temp_db):
    """Agent writes memory entry."""
    storage.add_entry("zealot-1", "space-dev", "Test entry")
    entries = storage.get_entries("zealot-1", "space-dev")
    assert len(entries) == 1
    assert entries[0].message == "Test entry"
    assert entries[0].topic == "space-dev"
    assert entries[0].identity == "zealot-1"


def test_read_by_topic(temp_db):
    """Agent reads specific topic."""
    storage.add_entry("zealot-1", "protoss", "Protoss work")
    storage.add_entry("zealot-1", "space-dev", "Space work")

    entries = storage.get_entries("zealot-1", "protoss")
    assert len(entries) == 1
    assert entries[0].message == "Protoss work"


def test_read_all_topics(temp_db):
    """Agent reads all topics."""
    storage.add_entry("zealot-1", "protoss", "Protoss work")
    storage.add_entry("zealot-1", "space-dev", "Space work")

    entries = storage.get_entries("zealot-1", None)
    assert len(entries) == 2


def test_edit_entry(temp_db):
    """Agent edits existing entry."""
    storage.add_entry("zealot-1", "space-dev", "Original")
    entries = storage.get_entries("zealot-1", "space-dev")
    entry_uuid = entries[0].uuid

    storage.edit_entry(entry_uuid, "Updated message")

    entries = storage.get_entries("zealot-1", "space-dev")
    assert len(entries) == 1
    assert entries[0].message == "Updated message"


def test_delete_entry(temp_db):
    """Agent deletes specific entry."""
    storage.add_entry("zealot-1", "space-dev", "Entry 1")
    storage.add_entry("zealot-1", "space-dev", "Entry 2")

    entries = storage.get_entries("zealot-1", "space-dev")
    assert len(entries) == 2

    storage.delete_entry(entries[0].uuid)

    entries = storage.get_entries("zealot-1", "space-dev")
    assert len(entries) == 1
    assert entries[0].message == "Entry 2"


def test_clear_topic(temp_db):
    """Agent clears entire topic."""
    storage.add_entry("zealot-1", "space-dev", "Entry 1")
    storage.add_entry("zealot-1", "space-dev", "Entry 2")
    storage.add_entry("zealot-1", "protoss", "Keep this")

    storage.clear_entries("zealot-1", "space-dev")

    space_entries = storage.get_entries("zealot-1", "space-dev")
    assert len(space_entries) == 0

    protoss_entries = storage.get_entries("zealot-1", "protoss")
    assert len(protoss_entries) == 1


def test_clear_all_topics(temp_db):
    """Agent clears all their memory."""
    storage.add_entry("zealot-1", "space-dev", "Entry 1")
    storage.add_entry("zealot-1", "protoss", "Entry 2")

    storage.clear_entries("zealot-1", None)

    entries = storage.get_entries("zealot-1", None)
    assert len(entries) == 0


def test_identity_isolation(temp_db):
    """Memory is identity-scoped."""
    storage.add_entry("zealot-1", "space-dev", "Zealot work")
    storage.add_entry("harbinger-1", "space-dev", "Harbinger work")

    zealot_entries = storage.get_entries("zealot-1", "space-dev")
    assert len(zealot_entries) == 1
    assert zealot_entries[0].message == "Zealot work"

    harbinger_entries = storage.get_entries("harbinger-1", "space-dev")
    assert len(harbinger_entries) == 1
    assert harbinger_entries[0].message == "Harbinger work"
