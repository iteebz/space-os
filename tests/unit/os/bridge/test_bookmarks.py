"""Tests for bridge bookmark tracking."""

import pytest

from space.lib.uuid7 import uuid7
from space.os.bridge import channels, messaging
from space.os.spawn import agents


@pytest.fixture
def test_channel(test_space):
    """Create a test channel."""
    return channels.create_channel("test-bookmarks", "Bookmark testing")


@pytest.fixture
def test_agent(test_space):
    """Create a test agent and return identity string."""
    identity = "bookmark-test-agent"
    agents.register_agent(
        identity=identity,
        constitution="zealot",
        model="claude-sonnet-4",
    )
    return identity


@pytest.mark.asyncio
async def test_recv_without_reader_returns_all_messages(test_space, test_channel, test_agent):
    """recv without reader_id returns all messages."""
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 2")
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 3")

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id)

    assert count == 3
    assert len(msgs) == 3


@pytest.mark.asyncio
async def test_recv_with_reader_tracks_bookmark(test_space, test_channel, test_agent):
    """recv with reader_id tracks bookmark and returns only unread."""
    reader_id = uuid7()

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 2")

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_id)
    assert count == 2

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 3")

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_id)
    assert count == 1
    assert msgs[0].content == "msg 3"


@pytest.mark.asyncio
async def test_recv_no_new_messages_returns_empty(test_space, test_channel, test_agent):
    """recv with bookmark at latest returns empty list."""
    reader_id = uuid7()

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")

    messaging.recv_messages(test_channel.channel_id, reader_id=reader_id)

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_id)
    assert count == 0
    assert len(msgs) == 0


@pytest.mark.asyncio
async def test_different_readers_independent_bookmarks(test_space, test_channel, test_agent):
    """Different readers have independent bookmarks."""
    reader_1 = uuid7()
    reader_2 = uuid7()

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 2")

    messaging.recv_messages(test_channel.channel_id, reader_id=reader_1)

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_2)
    assert count == 2

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 3")

    msgs_1, count_1, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_1)
    msgs_2, count_2, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_2)

    assert count_1 == 1
    assert count_2 == 1


@pytest.mark.asyncio
async def test_copy_bookmarks(test_space, test_channel, test_agent):
    """copy_bookmarks copies all bookmarks from one reader to another."""
    reader_1 = uuid7()
    reader_2 = uuid7()

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 2")

    messaging.recv_messages(test_channel.channel_id, reader_id=reader_1)

    messaging.copy_bookmarks(reader_1, reader_2)

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 3")

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_2)
    assert count == 1
    assert msgs[0].content == "msg 3"


@pytest.mark.asyncio
async def test_get_bookmark_returns_none_for_new_reader(test_space, test_channel):
    """get_bookmark returns None for reader with no bookmark."""
    reader_id = uuid7()

    result = messaging.get_bookmark(reader_id, test_channel.channel_id)
    assert result is None


@pytest.mark.asyncio
async def test_update_bookmark_creates_and_updates(test_space, test_channel, test_agent):
    """update_bookmark creates new bookmark and updates existing."""
    reader_id = uuid7()

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")
    msgs, _, _, _ = messaging.recv_messages(test_channel.channel_id)
    msg_1_id = msgs[0].message_id

    messaging.update_bookmark(reader_id, test_channel.channel_id, msg_1_id)

    result = messaging.get_bookmark(reader_id, test_channel.channel_id)
    assert result == msg_1_id

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 2")
    msgs, _, _, _ = messaging.recv_messages(test_channel.channel_id)
    msg_2_id = msgs[-1].message_id

    messaging.update_bookmark(reader_id, test_channel.channel_id, msg_2_id)

    result = messaging.get_bookmark(reader_id, test_channel.channel_id)
    assert result == msg_2_id


@pytest.mark.asyncio
async def test_first_recv_creates_bookmark_at_latest(test_space, test_channel, test_agent):
    """First recv with reader_id sets bookmark at latest message."""
    reader_id = uuid7()

    await messaging.send_message(test_channel.channel_id, test_agent, "msg 1")
    await messaging.send_message(test_channel.channel_id, test_agent, "msg 2")

    msgs, count, _, _ = messaging.recv_messages(test_channel.channel_id, reader_id=reader_id)
    assert count == 2

    bookmark = messaging.get_bookmark(reader_id, test_channel.channel_id)
    assert bookmark == msgs[-1].message_id
