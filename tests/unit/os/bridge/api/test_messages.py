from space.os.core.bridge import api


def test_send_message(test_space):
    channel_id = api.create_channel("test-channel")
    sender_agent_id = api.send_message(channel_id, "test-sender", "hello world")
    messages = api.fetch_messages(channel_id)
    assert len(messages) == 1
    assert messages[0].content == "hello world"
    assert messages[0].agent_id == sender_agent_id


def test_recv_updates(test_space):
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


def test_fetch_messages(test_space):
    channel_id = api.create_channel("fetch-channel")
    api.send_message(channel_id, "sender1", "message1")
    api.send_message(channel_id, "sender2", "message2")
    messages = api.fetch_messages(channel_id)
    assert len(messages) == 2
    assert messages[0].content == "message1"
    assert messages[1].content == "message2"


def test_fetch_sender_history(test_space):
    channel_id1 = api.create_channel("history-channel-1")
    channel_id2 = api.create_channel("history-channel-2")
    agent_name = "history-sender"

    api.send_message(channel_id1, agent_name, "message1")
    api.send_message(channel_id2, agent_name, "message2")
    api.send_message(channel_id1, "other-sender", "message3")

    history = api.fetch_agent_history(agent_name)
    assert len(history) == 2
    assert {msg.content for msg in history} == {"message1", "message2"}


def test_create_channel_with_topic(test_space):
    channel_name = "new-channel-with-topic"
    initial_topic = "This is the initial topic."
    channel_id = api.create_channel(channel_name, initial_topic)

    retrieved_topic = api.get_channel_topic(channel_id)
    assert retrieved_topic == initial_topic


def test_create_channel_without_topic(test_space):
    channel_name = "new-channel-without-topic"
    channel_id = api.create_channel(channel_name)

    retrieved_topic = api.get_channel_topic(channel_id)
    assert retrieved_topic is None


def test_active_channels_filter_unreads(test_space):
    channel1 = api.create_channel("active-1")
    channel2 = api.create_channel("active-2")
    channel3 = api.create_channel("active-3")
    agent_id = "test-agent"

    api.send_message(channel1, "sender", "msg1")
    api.send_message(channel2, "sender", "msg2")
    api.send_message(channel3, "sender", "msg3")

    active = api.active_channels(agent_id=agent_id)
    assert len(active) == 3

    api.recv_updates(channel1, agent_id)

    active = api.active_channels(agent_id=agent_id)
    assert len(active) == 2
    assert all(c.name in ["active-2", "active-3"] for c in active)


def test_active_channels_limit_five(test_space):
    agent_id = "test-agent"
    for i in range(7):
        channel_id = api.create_channel(f"channel-{i}")
        api.send_message(channel_id, "sender", f"msg-{i}")

    active = api.active_channels(agent_id=agent_id)
    assert len(active) == 5


def test_inbox_channels_all_unreads(test_space):
    agent_id = "test-agent"
    for i in range(7):
        channel_id = api.create_channel(f"inbox-{i}")
        api.send_message(channel_id, "sender", f"msg-{i}")

    inbox = api.inbox_channels(agent_id=agent_id)
    assert len(inbox) == 7

    first_channel = api.resolve_channel_id("inbox-0")
    api.recv_updates(first_channel, agent_id)

    inbox = api.inbox_channels(agent_id=agent_id)
    assert len(inbox) == 6


def test_recv_summary_latest(test_space):
    from space.os.core.bridge import api

    # Create a summary channel
    channel_id = api.create_channel("summary", topic="test summary topic")
    agent_id = "test-agent"

    # Send multiple messages to the summary channel
    api.send_message(channel_id, "sender1", "summary message 1")
    api.send_message(channel_id, "sender2", "summary message 2")
    api.send_message(channel_id, "sender3", "summary message 3")

    # Call recv_updates for the summary channel
    messages, count, _, _ = api.recv_updates(channel_id, agent_id)

    # This assertion should FAIL with the current implementation of recv_updates
    # because it will return all messages from db.get_new_messages.
    assert len(messages) == 1
    assert messages[0].content == "summary message 3"
    assert count == 1
