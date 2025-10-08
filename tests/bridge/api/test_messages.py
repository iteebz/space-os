from space.bridge import api
from space.bridge.storage import db as bridge_db


def test_send_message(bridge_workspace):
    """Verify that a sent message is stored and retrievable."""
    bridge_db.init_db()
    channel_id = api.create_channel("test-channel")
    api.send_message(channel_id, "test-sender", "hello world")
    messages = api.fetch_messages(channel_id)
    assert len(messages) == 1
    assert messages[0].content == "hello world"
    assert messages[0].sender == "test-sender"


def test_recv_updates(bridge_workspace):
    """Verify that recv_updates retrieves new messages and sets bookmarks."""
    bridge_db.init_db()
    channel_id = api.create_channel("recv-channel")
    agent_id = "test-agent"

    # First message
    api.send_message(channel_id, "sender1", "message1")
    messages, count, _, _ = api.recv_updates(channel_id, agent_id)
    assert count == 1
    assert messages[0].content == "message1"

    # Second message, should only receive this one
    api.send_message(channel_id, "sender2", "message2")
    messages, count, _, _ = api.recv_updates(channel_id, agent_id)
    assert count == 1
    assert messages[0].content == "message2"

    # No new messages
    messages, count, _, _ = api.recv_updates(channel_id, agent_id)
    assert count == 0
    assert len(messages) == 0


def test_fetch_messages(bridge_workspace):
    """Verify that fetch_messages retrieves all messages for a channel."""
    bridge_db.init_db()
    channel_id = api.create_channel("fetch-channel")
    api.send_message(channel_id, "sender1", "message1")
    api.send_message(channel_id, "sender2", "message2")
    messages = api.fetch_messages(channel_id)
    assert len(messages) == 2
    assert messages[0].content == "message1"
    assert messages[1].content == "message2"


def test_fetch_sender_history(bridge_workspace):
    """Verify that fetch_sender_history retrieves all messages from a sender."""
    bridge_db.init_db()
    channel_id1 = api.create_channel("history-channel-1")
    channel_id2 = api.create_channel("history-channel-2")
    sender_id = "history-sender"

    api.send_message(channel_id1, sender_id, "message1")
    api.send_message(channel_id2, sender_id, "message2")
    api.send_message(channel_id1, "other-sender", "message3")

    history = api.fetch_sender_history(sender_id)
    assert len(history) == 2
    assert {msg.content for msg in history} == {"message1", "message2"}


def test_create_channel_with_topic(bridge_workspace):
    """Verify that creating a channel with a topic correctly sets the topic."""
    bridge_db.init_db()
    channel_name = "new-channel-with-topic"
    initial_topic = "This is the initial topic."
    channel_id = api.create_channel(channel_name, initial_topic)

    retrieved_topic = api.get_channel_topic(channel_id)
    assert retrieved_topic == initial_topic


def test_create_channel_without_topic(bridge_workspace):
    """Verify that creating a channel without a topic results in a NULL topic."""
    bridge_db.init_db()
    channel_name = "new-channel-without-topic"
    channel_id = api.create_channel(channel_name)

    retrieved_topic = api.get_channel_topic(channel_id)
    assert retrieved_topic is None
