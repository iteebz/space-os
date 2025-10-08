import contextlib
import hashlib

import pytest

from space.bridge.api import channels, messages
from space.bridge.storage import db as bridge_db


@pytest.fixture
def setup_channel():
    bridge_db.init_db()
    channel_name = "test-archival-channel"
    identity = "test-agent"
    message_content = "This is a test message."
    dummy_file_content = "This is a dummy identity file."

    # Calculate the full SHA256 digest of the dummy file content
    constitution_hash = hashlib.sha256(dummy_file_content.encode()).hexdigest()

    # Register the identity with the correct topic and full hash
    from space.spawn import registry

    registry.register("test-role", identity, channel_name, constitution_hash)

    # Create a dummy identity file
    from space.spawn import config as spawn_config

    identity_file_path = spawn_config.bridge_identities_dir() / f"{identity}.md"
    identity_file_path.parent.mkdir(parents=True, exist_ok=True)
    identity_file_path.write_text(dummy_file_content)

    # Ensure channel is clean before test
    with contextlib.suppress(ValueError):
        channels.delete_channel(channel_name)

    channel_id = channels.create_channel(channel_name)
    messages.send_message(channel_id, identity, message_content)

    yield channel_name, channel_id, identity, message_content

    # Clean up after test
    with contextlib.suppress(ValueError):
        channels.delete_channel(channel_name)
    # Unregister the identity
    registry.unregister("test-role", identity, channel_name)
    # Delete the dummy identity file
    if identity_file_path.exists():
        identity_file_path.unlink()


def test_recv_does_not_return_messages_from_archived_channel(setup_channel):
    channel_name, channel_id, identity, message_content = setup_channel

    # Archive the channel
    channels.archive_channel(channel_name)

    # Attempt to receive messages from the archived channel
    msgs, unread_count, context, participants = messages.recv_updates(channel_id, identity)

    # Assert that no messages are returned
    assert len(msgs) == 0
    assert unread_count == 0
