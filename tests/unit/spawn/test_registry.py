from pathlib import Path
from unittest.mock import patch

import pytest

from space.spawn import registry


@pytest.fixture
def in_memory_db():
    """Fixture for an in-memory SQLite database."""
    with patch("space.spawn.config.registry_db", return_value=Path(":memory:")):
        registry.init_db()
        yield
        # No explicit teardown needed for in-memory db, it's destroyed when connection closes


def test_sender_id_not_unique(in_memory_db):
    """Verify that multiple entries can exist for the same sender_id."""
    registry.register(
        role="test_role",
        agent_id="test_sender",
        channels=["test-channel"],
        identity_hash="hash1",
        identity="content1",
    )
    registry.register(
        role="test_role",
        agent_id="test_sender",
        channels=["test-channel"],
        identity_hash="hash2",
        identity="content2",
    )

    with registry.get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM registry WHERE sender_id = 'test_sender'")
        count = cursor.fetchone()[0]
        assert count == 2


# def test_notes_column_functionality(in_memory_db):
#     """Verify that the notes column can be added and retrieved."""
#     registry.register(
#         role="test_role",
#         sender_id="test_sender_notes",
#         topic="test_topic",
#         identity_hash="hash_notes",
#         identity="content_notes",
#         model="model_notes",
#         notes="This is a test note.",
#     )
#
#     reg = registry.get_registration(
#         role="test_role", sender_id="test_sender_notes", topic="test_topic"
#     )
#     assert reg is not None
#     assert reg.notes == "This is a test note."
#
#     # Test with None notes
#     registry.register(
#         role="test_role",
#         sender_id="test_sender_no_notes",
#         topic="test_topic",
#         identity_hash="hash_no_notes",
#         identity="content_no_notes",
#         model="model_no_notes",
#         notes=None,
#     )
#     reg_no_notes = registry.get_registration(
#         role="test_role", sender_id="test_sender_no_notes", topic="test_topic"
#     )
#     assert reg_no_notes is not None
#     assert reg_no_notes.notes is None


# def test_get_registration_and_list_with_notes(in_memory_db):
#     """Verify that get_registration and list handle Registration objects with notes."""
#     registry.register(
#         role="role_list",
#         sender_id="sender_list_1",
#         topic="topic_list",
#         identity_hash="hash_list_1",
#         identity="content_list_1",
#         model="model_list_1",
#         notes="note_list_1",
#     )
#     registry.register(
#         role="role_list",
#         sender_id="sender_list_2",
#         topic="topic_list",
#         identity_hash="hash_list_2",
#         identity="content_list_2",
#         model="model_list_2",
#         notes="note_list_2",
#     )
#
#     # Test get_registration
#     reg1 = registry.get_registration(
#         role="role_list", sender_id="sender_list_1", topic="topic_list"
#     )
#     assert isinstance(reg1, Registration)
#     assert reg1.notes == "note_list_1"
#
#     # Test list
#     all_regs = registry.list()
#     assert len(all_regs) >= 2  # May have other entries from previous tests in the same db instance
#     found_reg1 = False
#     found_reg2 = False
#     for reg in all_regs:
#         if reg.sender_id == "sender_list_1":
#             assert reg.notes == "note_list_1"
#             found_reg1 = True
#         if reg.sender_id == "sender_list_2":
#             assert reg.notes == "note_list_2"
#             found_reg2 = True
#     assert found_reg1 and found_reg2


def test_multiple_entries_retrieved_chronologically(in_memory_db):
    """Verify that multiple entries for the same sender_id are retrieved chronologically."""
    # Register entries with different timestamps (mocking for chronological order)
    with registry.get_db() as conn:
        conn.execute(
            """
            INSERT INTO registry (role, agent_id, channels, constitution_hash, identity, registered_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "chrono_role",
                "chrono_sender",
                "chrono_channel",
                "hash_old",
                "content_old",
                "2023-01-01 10:00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO registry (role, agent_id, channels, constitution_hash, identity, registered_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "chrono_role",
                "chrono_sender",
                "chrono_channel",
                "hash_new",
                "content_new",
                "2023-01-01 11:00:00",
            ),
        )
        conn.commit()

    # Retrieve all entries for chrono_sender
    with registry.get_db() as conn:
        cursor = conn.execute(
            "SELECT constitution_hash, registered_at FROM registry WHERE agent_id = 'chrono_sender' ORDER BY registered_at ASC"
        )
        entries = cursor.fetchall()

    assert len(entries) == 2
    assert entries[0]["constitution_hash"] == "hash_old"
    assert entries[1]["constitution_hash"] == "hash_new"
    assert entries[0]["registered_at"] == "2023-01-01 10:00:00"
    assert entries[1]["registered_at"] == "2023-01-01 11:00:00"
