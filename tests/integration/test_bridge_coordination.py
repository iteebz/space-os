
import pytest

from space.os import bridge, spawn
from space.os.spawn.api import spawns


@pytest.mark.asyncio
async def test_agent_posts_mid_execution(test_space, default_agents):
    """Agents post autonomously mid-execution and wait for responses."""
    dev_channel_id = bridge.create_channel("space-dev", "Development coordination")
    zealot_1_id = default_agents["zealot"]
    zealot_2_id = default_agents["sentinel"]

    agent_z1_uuid = await bridge.send_message(
        dev_channel_id, zealot_1_id, "Starting analysis of spawn.py:42"
    )
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) == 1
    assert messages[0].agent_id == agent_z1_uuid

    await bridge.send_message(
        dev_channel_id,
        zealot_1_id,
        "Found potential bug at line 42. @sentinel please review before merge",
    )
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) >= 2
    assert "@sentinel" in messages[1].content

    new_for_zealot2, count, _, participants = bridge.recv_messages(dev_channel_id)
    assert count >= 2
    assert any("bug" in msg.content for msg in new_for_zealot2)

    await bridge.send_message(
        dev_channel_id,
        zealot_2_id,
        "Reviewed. Bug confirmed. Fix: change line 42 to `if x is None:`",
    )
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) >= 3
    assert any("Fix:" in msg.content for msg in messages)

    new_for_zealot1, count, _, _ = bridge.recv_messages(dev_channel_id)
    assert count >= 1
    assert any("Fix:" in msg.content for msg in new_for_zealot1)

    await bridge.send_message(dev_channel_id, zealot_1_id, "Implemented fix. Tests passing.")
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) >= 4


@pytest.mark.asyncio
async def test_full_spawn_ephemeral_events_flow(test_space, default_agents):
    """Agent creation → ephemeral creation → events emission data flow."""
    agent_identity = default_agents["zealot"]
    assert agent_identity is not None
    assert isinstance(agent_identity, str)
    assert len(agent_identity) > 0

    agent = spawn.get_agent(agent_identity)
    assert agent is not None
    agent_id = agent.agent_id

    ephemeral = spawns.create_spawn(
        agent_id=agent_id,
    )
    assert ephemeral is not None
    assert ephemeral.id is not None

    retrieved_ephemeral = spawns.get_spawn(ephemeral.id)
    assert retrieved_ephemeral is not None
    assert retrieved_ephemeral.agent_id == agent_id
    assert isinstance(retrieved_ephemeral.agent_id, str)

    spawns.update_status(ephemeral.id, "completed")
    updated_ephemeral = spawns.get_spawn(ephemeral.id)
    assert updated_ephemeral.status == "completed"
    assert updated_ephemeral.agent_id == agent_id
