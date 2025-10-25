"""Tests for bridge polling protocol."""

from space.os.core.bridge.ops.channels import resolve_channel_id
from space.os.core.bridge.ops.polls import create_poll, dismiss_poll, get_active_polls, is_polling
from space.os.core.bridge.ops.spawning import _parse_dismiss_command, _parse_poll_command
from space.os.core.spawn import db as spawn_db


def test_parse_poll_command():
    """Parse /poll @agent command."""
    cmd_type, agents = _parse_poll_command("/poll @hailot")
    assert cmd_type == "poll"
    assert "hailot" in agents


def test_parse_poll_command_multiple():
    """Parse /poll with multiple agents."""
    cmd_type, agents = _parse_poll_command("/poll @hailot @zealot")
    assert cmd_type == "poll"
    assert "hailot" in agents
    assert "zealot" in agents


def test_parse_dismiss_command():
    """Parse !agent dismissal command."""
    cmd_type, agents = _parse_dismiss_command("!hailot")
    assert cmd_type == "dismiss"
    assert "hailot" in agents


def test_parse_non_poll_command():
    """Non-poll content returns none."""
    cmd_type, agents = _parse_poll_command("@hailot what is 2+2?")
    assert cmd_type == "none"
    assert len(agents) == 0


def test_create_poll(test_space):
    """Create a poll record."""
    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = resolve_channel_id("test-channel")

    poll_id = create_poll(agent_id, channel_id, created_by="human")

    assert poll_id is not None
    assert len(poll_id) > 0


def test_is_polling(test_space):
    """Check if agent has active poll."""
    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = resolve_channel_id("test-channel")

    assert not is_polling(agent_id, channel_id)

    create_poll(agent_id, channel_id, created_by="human")

    assert is_polling(agent_id, channel_id)


def test_dismiss_poll(test_space):
    """Dismiss active poll."""
    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = resolve_channel_id("test-channel")

    create_poll(agent_id, channel_id, created_by="human")
    assert is_polling(agent_id, channel_id)

    dismissed = dismiss_poll(agent_id, channel_id)
    assert dismissed is True
    assert not is_polling(agent_id, channel_id)


def test_get_active_polls(test_space):
    """Get all active polls."""
    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = resolve_channel_id("test-channel")

    create_poll(agent_id, channel_id, created_by="human")

    polls = get_active_polls()
    assert len(polls) > 0
    assert polls[0]["agent_id"] == agent_id


def test_get_active_polls_by_channel(test_space):
    """Get active polls in specific channel."""
    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = resolve_channel_id("test-channel")

    create_poll(agent_id, channel_id, created_by="human")

    polls = get_active_polls(channel_id=channel_id)
    assert len(polls) > 0
    assert polls[0]["channel_id"] == channel_id


def test_dismiss_unknown_poll(test_space):
    """Dismissing non-existent poll returns False."""
    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = resolve_channel_id("test-channel")

    dismissed = dismiss_poll(agent_id, channel_id)
    assert dismissed is False


def test_multiple_polls_same_agent(test_space):
    """Agent can have polls in different channels."""
    agent_id = spawn_db.ensure_agent("hailot")
    ch1 = resolve_channel_id("channel-1")
    ch2 = resolve_channel_id("channel-2")

    create_poll(agent_id, ch1, created_by="human")
    create_poll(agent_id, ch2, created_by="human")

    polls = get_active_polls()
    hailot_polls = [p for p in polls if p["agent_id"] == agent_id]
    assert len(hailot_polls) == 2


def test_dismiss_only_specified_poll(test_space):
    """Dismiss only affects specified channel."""
    agent_id = spawn_db.ensure_agent("hailot")
    ch1 = resolve_channel_id("channel-1")
    ch2 = resolve_channel_id("channel-2")

    create_poll(agent_id, ch1, created_by="human")
    create_poll(agent_id, ch2, created_by="human")

    dismiss_poll(agent_id, ch1)

    assert not is_polling(agent_id, ch1)
    assert is_polling(agent_id, ch2)
