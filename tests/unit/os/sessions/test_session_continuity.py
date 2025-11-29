"""Unit tests for session continuity logic."""

from space.core.models import Agent
from space.os.bridge.api.delimiters import _get_last_session_in_channel
from space.os.sessions.api import operations
from space.os.spawn.api import spawns


def test_get_last_session_in_channel(test_space, default_agents):
    """_get_last_session_in_channel finds most recent session for agent in channel."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    agent = Agent(
        agent_id=zealot,
        identity="zealot",
        model="claude-sonnet-4-5",
        created_at="2024-01-01",
    )

    channel = bridge.create_channel("test-channel")

    # Create two completed spawns in channel with different sessions
    spawn1 = spawns.create_spawn(
        agent_id=agent.agent_id,
        channel_id=channel.channel_id,
    )
    spawns.update_status(spawn1.id, "completed")
    spawns.link_session_to_spawn(spawn1.id, "session-aaa")

    spawn2 = spawns.create_spawn(
        agent_id=agent.agent_id,
        channel_id=channel.channel_id,
    )
    spawns.update_status(spawn2.id, "completed")
    spawns.link_session_to_spawn(spawn2.id, "session-bbb")

    # Should return most recent session
    last_session = _get_last_session_in_channel(agent.agent_id, channel.channel_id)
    assert last_session == "session-bbb"


def test_get_last_session_different_channels_isolated(test_space, default_agents):
    """Sessions in different channels are isolated."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    agent = Agent(
        agent_id=zealot,
        identity="zealot",
        model="claude-sonnet-4-5",
        created_at="2024-01-01",
    )

    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")

    spawn_a = spawns.create_spawn(
        agent_id=agent.agent_id,
        channel_id=channel_a.channel_id,
    )
    spawns.update_status(spawn_a.id, "completed")
    spawns.link_session_to_spawn(spawn_a.id, "session-a")

    spawn_b = spawns.create_spawn(
        agent_id=agent.agent_id,
        channel_id=channel_b.channel_id,
    )
    spawns.update_status(spawn_b.id, "completed")
    spawns.link_session_to_spawn(spawn_b.id, "session-b")

    # Each channel should return its own session
    session_a = _get_last_session_in_channel(agent.agent_id, channel_a.channel_id)
    session_b = _get_last_session_in_channel(agent.agent_id, channel_b.channel_id)

    assert session_a == "session-a"
    assert session_b == "session-b"


def test_get_last_session_no_previous_returns_none(test_space, default_agents):
    """If no previous spawns in channel, returns None."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    channel = bridge.create_channel("fresh-channel")

    session = _get_last_session_in_channel(zealot, channel.channel_id)
    assert session is None


def test_resolve_session_no_resume_returns_none(test_space, default_agents):
    """resolve_session_id returns None when resume=None (discovery moved to call site)."""
    zealot = default_agents["zealot"]

    resolved = operations.resolve_session_id(
        agent_id=zealot,
        resume=None,
        provider="claude",
        identity="zealot",
    )
    assert resolved is None
