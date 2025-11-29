"""Unit tests for session continuity logic."""

from space.os.sessions.api import operations
from space.os.spawn.api import spawns


def test_active_spawn_session_used_for_continuity(test_space, default_agents):
    """Active spawn's session_id is used for session continuity on @mentions."""
    from space.os import bridge

    zealot = default_agents["zealot"]

    channel = bridge.create_channel("test-channel")

    spawn = spawns.create_spawn(agent_id=zealot, channel_id=channel.channel_id)
    spawns.update_status(spawn.id, "active")
    spawns.link_session_to_spawn(spawn.id, "session-abc")

    found = spawns.get_active_spawn_in_channel(zealot, channel.channel_id)
    assert found is not None
    assert found.session_id == "session-abc"


def test_session_continuity_channel_isolation(test_space, default_agents):
    """Active spawns in different channels have isolated sessions."""
    from space.os import bridge

    zealot = default_agents["zealot"]

    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")

    spawn_a = spawns.create_spawn(agent_id=zealot, channel_id=channel_a.channel_id)
    spawns.update_status(spawn_a.id, "active")
    spawns.link_session_to_spawn(spawn_a.id, "session-a")

    spawn_b = spawns.create_spawn(agent_id=zealot, channel_id=channel_b.channel_id)
    spawns.update_status(spawn_b.id, "active")
    spawns.link_session_to_spawn(spawn_b.id, "session-b")

    found_a = spawns.get_active_spawn_in_channel(zealot, channel_a.channel_id)
    found_b = spawns.get_active_spawn_in_channel(zealot, channel_b.channel_id)

    assert found_a.session_id == "session-a"
    assert found_b.session_id == "session-b"


def test_no_active_spawn_returns_none(test_space, default_agents):
    """If no active spawn in channel, returns None."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    channel = bridge.create_channel("fresh-channel")

    found = spawns.get_active_spawn_in_channel(zealot, channel.channel_id)
    assert found is None


def test_resolve_session_no_resume_returns_none(test_space, default_agents):
    """resolve_session_id returns None when resume=None."""
    zealot = default_agents["zealot"]

    resolved = operations.resolve_session_id(
        agent_id=zealot,
        resume=None,
        provider="claude",
        identity="zealot",
    )
    assert resolved is None
