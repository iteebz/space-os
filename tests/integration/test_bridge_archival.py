import contextlib
import hashlib

import pytest

from space.bridge.api import channels, messages
from space.errors import ChannelNotFoundError


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

    registry.register("test-role", identity, channel_name, constitution_hash)

    # Create a dummy identity file
    from space.spawn import config as spawn_config

    identity_file_path = spawn_config.bridge_identities_dir() / f"{identity}.md"
    identity_file_path.parent.mkdir(parents=True, exist_ok=True)
    identity_file_path.write_text(dummy_file_content)

    # Ensure channel is clean before test
    with contextlib.suppress(ChannelNotFoundError):
        channels.delete_channel(channel_name)

    channel_id = channels.create_channel(channel_name)
    messages.send_message(channel_id, identity, message_content)

    yield channel_name, channel_id, identity, message_content

    # Clean up after test
    with contextlib.suppress(ChannelNotFoundError):
        channels.delete_channel(channel_name)
    # Unregister the identity
    registry.unregister("test-role", identity, channel_name)
    # Delete the dummy identity file
    if identity_file_path.exists():
        identity_file_path.unlink()


def test_recv_ignores_archived_channel_messages(setup_channel):
    channel_name, channel_id, identity, message_content = setup_channel

    channels.archive_channel(channel_name)

    msgs, unread_count, topic, participants = messages.recv_updates(channel_id, identity)

    assert len(msgs) == 0
    assert unread_count == 0


def test_inbox_excludes_archived_channels(setup_channel):
    channel_name, channel_id, identity, message_content = setup_channel

    inbox_before = channels.inbox_channels(identity)
    test_channel_count = sum(1 for c in inbox_before if c.name == channel_name)
    assert test_channel_count == 1

    channels.archive_channel(channel_name)

    inbox_after = channels.inbox_channels(identity)
    test_channel_count_after = sum(1 for c in inbox_after if c.name == channel_name)
    assert test_channel_count_after == 0


def test_all_channels_marks_archived_channels(setup_channel):
    channel_name, channel_id, identity, message_content = setup_channel

    channels.archive_channel(channel_name)

    all_channel_records = channels.all_channels()
    matched = [c for c in all_channel_records if c.name == channel_name]

    assert matched
    assert matched[0].archived_at is not None
