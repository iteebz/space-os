import contextlib
import hashlib

import pytest

from space.apps.bridge import coordination
from space.apps.bridge.coordination import messages as coordination_messages


@pytest.fixture
def setup_channel():
    channel_name = "test-archival-channel"
    identity = "test-agent"
    message_content = "This is a test message."
    dummy_file_content = "This is a dummy identity file."

    # Calculate the full SHA256 digest of the dummy file content
    constitution_hash = hashlib.sha256(dummy_file_content.encode()).hexdigest()

    # Register the identity with the correct topic and full hash
    from space.spawn import registry

    registry.register(
        "test-role",
        identity,
        channel_name,
        identity_hash=constitution_hash,
        identity=dummy_file_content,
    )

    # Initialize the database to ensure schema is up-to-date
    from space.apps.bridge.storage import db as bridge_db

    bridge_db.init_db()

    # Ensure channel is clean before test
    with contextlib.suppress(ValueError):
        coordination.delete_channel(channel_name)

    channel_id = coordination.create_channel(channel_name)
    coordination.send_message(channel_id, identity, message_content)

    yield channel_name, channel_id, identity, message_content

    # Clean up after test
    with contextlib.suppress(ValueError):
        coordination.delete_channel(channel_name)
        # Unregister the identity
        registry.unregister(identity, channel_name)


def test_recv_does_not_return_messages_from_archived_channel(setup_channel):
    channel_name, channel_id, identity, message_content = setup_channel

    # Archive the channel
    coordination.archive_channel(channel_name)

    # Attempt to receive messages from the archived channel
    messages, unread_count, context, participants = coordination_messages.recv_updates(
        channel_id, identity
    )

    # Assert that no messages are returned
    assert len(messages) == 0
    assert unread_count == 0
