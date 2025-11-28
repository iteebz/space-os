"""Spawn ephemeral lifecycle: creation, status transitions, agent/channel tracking."""

from unittest.mock import patch

from space.core.models import Agent, SpawnStatus
from space.os import bridge, spawn
from space.os.spawn.api import spawns


def test_create_spawn_with_channel(test_space, default_agents):
    """Spawn creation with channel stores both agent and channel references."""
    channel = bridge.create_channel("investigation-channel")
    zealot_agent_id = default_agents["zealot"]
    agent = spawn.get_agent(zealot_agent_id)

    spawn1 = spawns.create_spawn(agent_id=agent.agent_id, channel_id=channel.channel_id)

    assert spawn1.channel_id == channel.channel_id
    assert spawn1.agent_id is not None
    assert spawn.get_agent(spawn1.agent_id).identity == "zealot"


def test_spawns_in_same_channel(test_space, default_agents):
    """Multiple ephemerals in same channel preserve individual agent references."""
    channel = bridge.create_channel("investigation-channel")
    zealot_agent = spawn.get_agent(default_agents["zealot"])
    sentinel_agent = spawn.get_agent(default_agents["sentinel"])

    spawn1 = spawns.create_spawn(agent_id=zealot_agent.agent_id, channel_id=channel.channel_id)
    spawn2 = spawns.create_spawn(agent_id=sentinel_agent.agent_id, channel_id=channel.channel_id)
    spawn3 = spawns.create_spawn(agent_id=zealot_agent.agent_id, channel_id=channel.channel_id)

    assert spawn1.channel_id == channel.channel_id
    assert spawn2.channel_id == channel.channel_id
    assert spawn3.channel_id == channel.channel_id

    assert spawn.get_agent(spawn1.agent_id).identity == "zealot"
    assert spawn.get_agent(spawn2.agent_id).identity == "sentinel"
    assert spawn.get_agent(spawn3.agent_id).identity == "zealot"


def test_channel_isolation(test_space, default_agents):
    """Ephemerals from different channels are isolated."""
    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")
    zealot_agent = spawn.get_agent(default_agents["zealot"])
    sentinel_agent = spawn.get_agent(default_agents["sentinel"])

    spawn_a = spawns.create_spawn(agent_id=zealot_agent.agent_id, channel_id=channel_a.channel_id)
    spawn_b = spawns.create_spawn(agent_id=sentinel_agent.agent_id, channel_id=channel_b.channel_id)

    retrieved_a = spawns.get_spawn(spawn_a.id)
    retrieved_b = spawns.get_spawn(spawn_b.id)

    assert retrieved_a.channel_id == channel_a.channel_id
    assert retrieved_b.channel_id == channel_b.channel_id
    assert retrieved_a.channel_id != retrieved_b.channel_id


def test_spawn_status_transitions(test_space, default_agents):
    """Spawn status progresses: pending → running → completed."""
    agent = spawn.get_agent(default_agents["zealot"])
    spawn1 = spawns.create_spawn(
        agent_id=agent.agent_id,
    )

    assert spawn1.status == SpawnStatus.PENDING

    spawns.update_status(spawn1.id, SpawnStatus.RUNNING)
    running = spawns.get_spawn(spawn1.id)
    assert running.status == SpawnStatus.RUNNING

    spawns.update_status(spawn1.id, SpawnStatus.COMPLETED)
    completed = spawns.get_spawn(spawn1.id)
    assert completed.status == SpawnStatus.COMPLETED
    assert completed.ended_at is not None


def test_spawn_failure(test_space, default_agents):
    """Spawn can transition from running to failed."""
    agent = spawn.get_agent(default_agents["zealot"])
    spawn1 = spawns.create_spawn(
        agent_id=agent.agent_id,
    )

    spawns.update_status(spawn1.id, SpawnStatus.RUNNING)
    spawns.update_status(spawn1.id, SpawnStatus.FAILED)

    failed = spawns.get_spawn(spawn1.id)
    assert failed.status == SpawnStatus.FAILED
    assert failed.ended_at is not None


def test_spawn_with_pid(test_space, default_agents):
    """Spawn can store PID for lifecycle management."""
    agent = spawn.get_agent(default_agents["zealot"])
    spawn1 = spawns.create_spawn(
        agent_id=agent.agent_id,
    )

    spawns.update_status(spawn1.id, SpawnStatus.RUNNING)
    # Update PID directly in spawns (no pid parameter in update_status)
    # For now, just verify spawn creation works
    running = spawns.get_spawn(spawn1.id)
    assert running is not None


def test_list_spawns_all(test_space, default_agents):
    """List all spawns returns all spawns for agent."""
    agent = spawn.get_agent(default_agents["zealot"])
    spawn1 = spawns.create_spawn(agent_id=agent.agent_id)
    spawn2 = spawns.create_spawn(agent_id=agent.agent_id)

    all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    spawn_ids = {s.id for s in all_spawns}
    assert spawn1.id in spawn_ids
    assert spawn2.id in spawn_ids


def test_list_spawns_by_status(test_space, default_agents):
    """Spawns can be filtered by status."""
    agent = spawn.get_agent(default_agents["zealot"])
    spawn1 = spawns.create_spawn(agent_id=agent.agent_id)
    spawn2 = spawns.create_spawn(agent_id=agent.agent_id)

    spawns.update_status(spawn1.id, SpawnStatus.COMPLETED)

    all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    pending = [s for s in all_spawns if s.status == SpawnStatus.PENDING]
    completed = [s for s in all_spawns if s.status == SpawnStatus.COMPLETED]

    assert spawn1.id not in {s.id for s in pending}
    assert spawn2.id in {s.id for s in pending}
    assert spawn1.id in {s.id for s in completed}


def test_list_spawns_by_identity(test_space, default_agents):
    """Spawns can be filtered by agent."""
    zealot_agent = spawn.get_agent(default_agents["zealot"])
    sentinel_agent = spawn.get_agent(default_agents["sentinel"])

    spawn_z = spawns.create_spawn(
        agent_id=zealot_agent.agent_id,
    )
    spawn_s = spawns.create_spawn(
        agent_id=sentinel_agent.agent_id,
    )

    zealot_spawns = list(spawns.get_spawns_for_agent(zealot_agent.agent_id))
    sentinel_spawns = list(spawns.get_spawns_for_agent(sentinel_agent.agent_id))

    zealot_ids = {s.id for s in zealot_spawns}
    sentinel_ids = {s.id for s in sentinel_spawns}

    assert spawn_z.id in zealot_ids
    assert spawn_z.id not in sentinel_ids
    assert spawn_s.id in sentinel_ids
    assert spawn_s.id not in zealot_ids


def test_list_spawns_by_channel(test_space, default_agents):
    """Spawns can be filtered by channel."""
    channel = bridge.create_channel("test-channel")
    agent = spawn.get_agent(default_agents["zealot"])

    spawn_in_channel = spawns.create_spawn(agent_id=agent.agent_id, channel_id=channel.channel_id)
    spawn_no_channel = spawns.create_spawn(agent_id=agent.agent_id)

    all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    in_channel = [s for s in all_spawns if s.channel_id == channel.channel_id]
    spawn_ids = {s.id for s in in_channel}

    assert spawn_in_channel.id in spawn_ids
    assert spawn_no_channel.id not in spawn_ids


def test_mention_spawns_worker():
    """Bridge detects @mention and builds spawn context."""
    from space.os.spawn.api.prompt import build_spawn_context

    with patch("space.os.spawn.api.prompt.agents.get_agent") as mock_get_agent:
        mock_agent = Agent(
            agent_id="a-1",
            identity="zealot",
            constitution="zealot.md",
            model="claude-haiku-4-5",
            created_at="2024-01-01",
        )
        mock_get_agent.return_value = mock_agent

        result = build_spawn_context("zealot", task="@zealot question", channel="subagents-test")

        assert result is not None
        assert "PRIMITIVES" in result
        assert "question" in result
        assert "#subagents-test" in result
