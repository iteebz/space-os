import pytest

from space.core.models import HandoffStatus
from space.os import bridge, spawn


@pytest.mark.asyncio
async def test_create_channel_with_topic(test_space):
    channel_name = "new-channel-with-topic"
    initial_topic = "This is the initial topic."
    channel = bridge.create_channel(channel_name, initial_topic)

    retrieved = bridge.get_channel(channel)
    assert retrieved.topic == initial_topic


@pytest.mark.asyncio
async def test_create_channel_without_topic(test_space):
    channel_name = "new-channel-without-topic"
    channel = bridge.create_channel(channel_name)

    retrieved = bridge.get_channel(channel)
    assert retrieved.topic is None


@pytest.mark.asyncio
async def test_fetch_sender_history(test_space, default_agents):
    channel_id1 = bridge.create_channel("history-channel-1")
    channel_id2 = bridge.create_channel("history-channel-2")
    agent_name = default_agents["zealot"]

    await bridge.send_message(channel_id1, agent_name, "message1")
    await bridge.send_message(channel_id2, agent_name, "message2")
    spawn.register_agent("other-sender", "claude-haiku-4-5")
    await bridge.send_message(channel_id1, "other-sender", "message3")

    history = bridge.get_sender_history(agent_name)
    assert len(history) == 2
    assert {msg.content for msg in history} == {"message1", "message2"}


def test_create_handoff(test_space, default_agents):
    channel = bridge.create_channel("handoff-test")
    spawn.register_agent("recipient", "claude-haiku-4-5")

    h = bridge.create_handoff(channel.name, "zealot", "recipient", "work ready for review")

    assert h.handoff_id is not None
    assert h.status == HandoffStatus.PENDING
    assert h.summary == "work ready for review"

    msgs = bridge.get_messages(channel)
    assert len(msgs) == 1
    assert "@recipient handoff:" in msgs[0].content


def test_close_handoff(test_space, default_agents):
    channel = bridge.create_channel("close-test")
    spawn.register_agent("target", "claude-haiku-4-5")

    h = bridge.create_handoff(channel.name, "zealot", "target", "task done")
    assert h.status == HandoffStatus.PENDING

    closed = bridge.close_handoff(h.handoff_id)
    assert closed.status == HandoffStatus.CLOSED
    assert closed.closed_at is not None


def test_list_pending_handoffs(test_space, default_agents):
    channel = bridge.create_channel("pending-test")
    spawn.register_agent("worker", "claude-haiku-4-5")

    bridge.create_handoff(channel.name, "zealot", "worker", "task 1")
    bridge.create_handoff(channel.name, "zealot", "worker", "task 2")

    pending = bridge.list_pending(to_identity="worker")
    assert len(pending) == 2

    bridge.close_handoff(pending[0].handoff_id)

    pending_after = bridge.list_pending(to_identity="worker")
    assert len(pending_after) == 1


def test_list_pending_by_channel(test_space, default_agents):
    ch1 = bridge.create_channel("inbox-ch1")
    ch2 = bridge.create_channel("inbox-ch2")
    spawn.register_agent("reviewer", "claude-haiku-4-5")

    bridge.create_handoff(ch1.name, "zealot", "reviewer", "from ch1")
    bridge.create_handoff(ch2.name, "zealot", "reviewer", "from ch2")

    all_pending = bridge.list_pending(to_identity="reviewer")
    assert len(all_pending) == 2

    ch1_only = bridge.list_pending(to_identity="reviewer", channel=ch1.name)
    assert len(ch1_only) == 1
    assert ch1_only[0].summary == "from ch1"
