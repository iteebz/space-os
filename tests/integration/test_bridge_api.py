from space.os import bridge, spawn


def test_create_channel_with_topic(test_space):
    channel_name = "new-channel-with-topic"
    initial_topic = "This is the initial topic."
    channel = bridge.create_channel(channel_name, initial_topic)

    retrieved = bridge.get_channel(channel)
    assert retrieved.topic == initial_topic


def test_create_channel_without_topic(test_space):
    channel_name = "new-channel-without-topic"
    channel = bridge.create_channel(channel_name)

    retrieved = bridge.get_channel(channel)
    assert retrieved.topic is None


def test_active_channels_filter_unreads(test_space, default_agents):
    channel1 = bridge.create_channel("active-1")
    channel2 = bridge.create_channel("active-2")
    channel3 = bridge.create_channel("active-3")
    identity = default_agents["zealot"]

    # Get the actual agent ID (UUID)
    agent = spawn.get_agent(identity)
    assert agent is not None
    agent_id = agent.agent_id

    bridge.send_message(channel1, "zealot", "msg1")
    bridge.send_message(channel2, "zealot", "msg2")
    bridge.send_message(channel3, "zealot", "msg3")

    active = bridge.list_channels(agent_id=agent_id)
    assert len(active) == 3

    bridge.recv_messages(channel1, identity)

    active = bridge.list_channels(agent_id=agent_id)
    assert len(active) == 2
    assert all(c.name in ["active-2", "active-3"] for c in active)


def test_active_channels_limit_five(test_space, default_agents):
    identity = default_agents["zealot"]
    agent = spawn.get_agent(identity)
    assert agent is not None
    agent_id = agent.agent_id

    for i in range(7):
        channel = bridge.create_channel(f"channel-{i}")
        bridge.send_message(channel, "zealot", f"msg-{i}")

    active = bridge.list_channels(agent_id=agent_id)
    assert len(active) == 5


def test_inbox_channels_all_unreads(test_space, default_agents):
    identity = default_agents["zealot"]
    agent = spawn.get_agent(identity)
    assert agent is not None
    agent_id = agent.agent_id

    for i in range(7):
        channel = bridge.create_channel(f"inbox-{i}")
        bridge.send_message(channel, "zealot", f"msg-{i}")

        inbox = bridge.fetch_inbox(agent_id=agent_id)

    first_channel = bridge.resolve_channel("inbox-0")
    bridge.recv_messages(first_channel, identity)

    inbox = bridge.fetch_inbox(agent_id=agent_id)
    assert len(inbox) == 6


def test_fetch_sender_history(test_space, default_agents):
    from space.os import spawn

    channel_id1 = bridge.create_channel("history-channel-1")
    channel_id2 = bridge.create_channel("history-channel-2")
    agent_name = default_agents["zealot"]

    bridge.send_message(channel_id1, agent_name, "message1")
    bridge.send_message(channel_id2, agent_name, "message2")
    spawn.register_agent("other-sender", "claude-haiku-4-5")
    bridge.send_message(channel_id1, "other-sender", "message3")

    history = bridge.get_sender_history(agent_name)
    assert len(history) == 2
    assert {msg.content for msg in history} == {"message1", "message2"}


def test_bookmark_respects_bookmarks(test_space, default_agents):
    channel_id = bridge.create_channel("bookmark-channel")
    # Use sentinel instead of registering a new agent
    identity = "sentinel"

    bridge.send_message(channel_id, "zealot", "first message")
    messages, unread_count, _, _ = bridge.recv_messages(channel_id, identity)
    assert [msg.content for msg in messages] == ["first message"]
    assert unread_count == 1

    bridge.send_message(channel_id, "zealot", "second message")
    messages, unread_count, _, _ = bridge.recv_messages(channel_id, identity)
    assert [msg.content for msg in messages] == ["second message"]
    assert unread_count == 1


def test_get_messages_mixed_id_types(test_space, default_agents):
    channel_id = bridge.create_channel("mixed-ids")
    agent_identity = default_agents["zealot"]
    agent = spawn.get_agent(agent_identity)
    assert agent is not None
    agent_id = agent.agent_id

    bridge.send_message(channel_id, "zealot", "uuid message 1")
    bridge.send_message(channel_id, "sentinel", "uuid message 2")
    bridge.send_message(channel_id, "crucible", "integer message")
    bridge.send_message(channel_id, "zealot", "uuid message 3")

    messages = bridge.get_messages(channel_id, agent_id)
    assert len(messages) == 4
    assert messages[0].content == "uuid message 1"
    assert messages[1].content == "uuid message 2"
    assert messages[2].content == "integer message"
    assert messages[3].content == "uuid message 3"

    bridge.set_bookmark(agent_id, channel_id, messages[1].message_id)

    new_msgs = bridge.get_messages(channel_id, agent_id)
    assert len(new_msgs) == 2
    assert new_msgs[0].content == "integer message"
    assert new_msgs[1].content == "uuid message 3"


def test_recv_summary_latest(test_space, default_agents):
    channel_id = bridge.create_channel("summary", topic="test summary topic")
    agent_identity = default_agents["zealot"]
    agent = spawn.get_agent(agent_identity)
    assert agent is not None

    bridge.send_message(channel_id, "zealot", "summary message 1")
    bridge.send_message(channel_id, "sentinel", "summary message 2")
    bridge.send_message(channel_id, "crucible", "summary message 3")

    messages, count, _, _ = bridge.recv_messages(channel_id, agent_identity)

    assert len(messages) == 3
    assert count == 3
    assert messages[0].content == "summary message 1"
    assert messages[1].content == "summary message 2"
    assert messages[2].content == "summary message 3"

    messages, count, _, _ = bridge.recv_messages(channel_id, agent_identity)
    assert len(messages) == 0
    assert count == 0


def test_note_convert_identity(test_space, default_agents):
    channel_id = bridge.create_channel("note-test-channel")
    identity = default_agents["zealot"]
    agent = spawn.get_agent(identity)
    assert agent is not None
    agent_id = agent.agent_id

    bridge.add_note(channel_id, identity, "test note content")

    notes = bridge.get_notes(channel_id)
    assert len(notes) == 1
    assert notes[0].agent_id == agent_id
    assert notes[0].content == "test note content"


def test_notes_return_agent_id(test_space, default_agents):
    channel_id = bridge.create_channel("note-uuid-test")
    identity = default_agents["zealot"]
    agent = spawn.get_agent(identity)
    assert agent is not None
    agent_id = agent.agent_id

    bridge.add_note(channel_id, identity, "note content")

    notes = bridge.get_notes(channel_id)
    assert len(notes) == 1

    assert hasattr(notes[0], "agent_id")
    assert notes[0].agent_id == agent_id
    assert isinstance(notes[0].agent_id, str)
    assert len(notes[0].agent_id) == 36
