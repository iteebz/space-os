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


def test_fetch_sender_history(test_space, default_agents):
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
