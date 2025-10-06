import pytest
from pathlib import Path
import sqlite3

# Import the API functions
from space.apps.memory.api import (
    add_memory_entry,
    get_memory_entries,
    edit_memory_entry,
    delete_memory_entry,
    clear_memory_entries,
)
from space.apps.memory.models import Memory
from space.apps.memory.app import memory_app # To set the db_path for the app

# Mock the app.db_path for the API functions to use the temporary database
@pytest.fixture(autouse=True)
def mock_app_db_path(memory_db_path):
    original_db_path = memory_app.db_path
    memory_app._db_path = memory_db_path
    yield
    memory_app._db_path = original_db_path

def test_add_and_get_memory_entry():
    identity = "test_agent"
    topic = "test_topic"
    message = "This is a test message."

    add_memory_entry(identity, topic, message)

    entries = get_memory_entries(identity, topic)
    assert len(entries) == 1
    assert entries[0].identity == identity
    assert entries[0].topic == topic
    assert entries[0].message == message

def test_get_memory_entries_by_identity_only():
    identity1 = "test_agent1"
    identity2 = "test_agent2"
    topic1 = "topic_a"
    topic2 = "topic_b"

    add_memory_entry(identity1, topic1, "message 1a")
    add_memory_entry(identity1, topic2, "message 1b")
    add_memory_entry(identity2, topic1, "message 2a")

    entries = get_memory_entries(identity1)
    assert len(entries) == 2
    assert all(e.identity == identity1 for e in entries)

    entries = get_memory_entries(identity2)
    assert len(entries) == 1
    assert all(e.identity == identity2 for e in entries)

def test_edit_memory_entry():
    identity = "test_agent"
    topic = "test_topic"
    original_message = "Original message."
    new_message = "Updated message."

    add_memory_entry(identity, topic, original_message)
    entries = get_memory_entries(identity, topic)
    entry_uuid = entries[0].uuid

    edit_memory_entry(entry_uuid, new_message)
    updated_entries = get_memory_entries(identity, topic)
    assert len(updated_entries) == 1
    assert updated_entries[0].message == new_message

def test_delete_memory_entry():
    identity = "test_agent"
    topic = "test_topic"
    message1 = "Message one."
    message2 = "Message two."

    add_memory_entry(identity, topic, message1)
    add_memory_entry(identity, topic, message2)
    entries = get_memory_entries(identity, topic)
    entry_uuid_to_delete = entries[0].uuid

    delete_memory_entry(entry_uuid_to_delete)
    remaining_entries = get_memory_entries(identity, topic)
    assert len(remaining_entries) == 1
    assert remaining_entries[0].message == message1

def test_clear_memory_entries_by_topic():
    identity = "test_agent"
    topic1 = "topic_x"
    topic2 = "topic_y"

    add_memory_entry(identity, topic1, "message x1")
    add_memory_entry(identity, topic1, "message x2")
    add_memory_entry(identity, topic2, "message y1")

    clear_memory_entries(identity, topic1)
    remaining_x = get_memory_entries(identity, topic1)
    assert len(remaining_x) == 0
    remaining_y = get_memory_entries(identity, topic2)
    assert len(remaining_y) == 1

def test_clear_all_memory_entries_for_identity():
    identity1 = "test_agent1"
    identity2 = "test_agent2"
    topic1 = "topic_a"
    topic2 = "topic_b"

    add_memory_entry(identity1, topic1, "message 1a")
    add_memory_entry(identity1, topic2, "message 1b")
    add_memory_entry(identity2, topic1, "message 2a")

    clear_memory_entries(identity1)
    remaining_1 = get_memory_entries(identity1)
    assert len(remaining_1) == 0
    remaining_2 = get_memory_entries(identity2)
    assert len(remaining_2) == 1

def test_edit_non_existent_entry_raises_error():
    with pytest.raises(ValueError, match="No entry found with UUID"): # Updated regex to match the exact error message
        edit_memory_entry("non_existent_uuid", "new message")

def test_delete_non_existent_entry_raises_error():
    with pytest.raises(ValueError, match="No entry found with UUID"): # Updated regex to match the exact error message
        delete_memory_entry("non_existent_uuid")

# Skipping ambiguous UUID test for now at the API level, as _resolve_uuid is an internal helper.
# The API functions will simply propagate the ValueError from _resolve_uuid.
