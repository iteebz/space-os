def test_recv_respects_bookmarks(test_space):
    from space.os.core.bridge import api
    from space.os.core.bridge.api import messages as coordination_messages

    channel_id = api.create_channel("bookmark-channel")

    api.send_message(channel_id, "human", "first message")
    messages, unread_count, _, _ = coordination_messages.recv_updates(channel_id, "agent-a")
    assert [msg.content for msg in messages] == ["first message"]
    assert unread_count == 1

    api.send_message(channel_id, "human", "second message")
    messages, unread_count, _, _ = coordination_messages.recv_updates(channel_id, "agent-a")
    assert [msg.content for msg in messages] == ["second message"]
    assert unread_count == 1


def test_get_new_messages_summary_channel_no_special_handling(test_space):
    from space.os.core.bridge import api, db

    # Create a summary channel
    channel_id = db.create_channel("summary", topic="test summary topic")
    agent_id = "test-agent"

    # Send multiple messages to the summary channel
    api.send_message(channel_id, "sender1", "summary message 1")
    api.send_message(channel_id, "sender2", "summary message 2")
    api.send_message(channel_id, "sender3", "summary message 3")

    # This test expects get_new_messages to *not* have special handling for "summary"
    # and thus return all new messages.
    messages = db.get_new_messages(channel_id, agent_id)

    # This assertion should FAIL with the current implementation of get_new_messages
    # because it will only return the last message.
    assert len(messages) == 3
    assert messages[0].content == "summary message 1"
    assert messages[1].content == "summary message 2"
    assert messages[2].content == "summary message 3"


def test_get_new_messages_mixed_id_types(test_space):
    from space.os.core.bridge import db

    channel_id = db.create_channel("mixed-ids")
    agent_id = "test-agent"

    conn = db.connect()

    db.create_message(channel_id, "agent1", "uuid message 1")
    db.create_message(channel_id, "agent2", "uuid message 2")

    conn.execute(
        "INSERT INTO messages (message_id, channel_id, agent_id, content, priority) VALUES (?, ?, ?, ?, ?)",
        ("999", channel_id, "agent3", "integer message", "normal"),
    )
    conn.commit()

    db.create_message(channel_id, "agent4", "uuid message 3")

    messages = db.get_new_messages(channel_id, agent_id)
    assert len(messages) == 4
    assert messages[0].content == "uuid message 1"
    assert messages[1].content == "uuid message 2"
    assert messages[2].content == "integer message"
    assert messages[3].content == "uuid message 3"

    db.set_bookmark(agent_id, channel_id, messages[1].message_id)

    new_msgs = db.get_new_messages(channel_id, agent_id)
    assert len(new_msgs) == 2
    assert new_msgs[0].content == "integer message"
    assert new_msgs[1].content == "uuid message 3"
