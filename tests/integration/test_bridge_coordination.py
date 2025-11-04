import time

from space.core.models import TaskStatus
from space.os import bridge, spawn
from space.os.spawn.api import spawns


def test_agent_posts_mid_execution(test_space, default_agents):
    """Agents post autonomously mid-execution and wait for responses."""
    dev_channel_id = bridge.create_channel("space-dev", "Development coordination")
    zealot_1_id = default_agents["zealot"]
    zealot_2_id = default_agents["sentinel"]

    agent_z1_uuid = bridge.send_message(
        dev_channel_id, zealot_1_id, "Starting analysis of spawn.py:42"
    )
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) == 1
    assert messages[0].agent_id == agent_z1_uuid

    bridge.send_message(
        dev_channel_id,
        zealot_1_id,
        "Found potential bug at line 42. @sentinel please review before merge",
    )
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) >= 2
    assert "@sentinel" in messages[1].content

    new_for_zealot2, count, _, participants = bridge.recv_messages(dev_channel_id, zealot_2_id)
    assert count >= 2
    assert any("bug" in msg.content for msg in new_for_zealot2)

    bridge.send_message(
        dev_channel_id,
        zealot_2_id,
        "Reviewed. Bug confirmed. Fix: change line 42 to `if x is None:`",
    )
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) >= 3
    assert any("Fix:" in msg.content for msg in messages)

    new_for_zealot1, count, _, _ = bridge.recv_messages(dev_channel_id, zealot_1_id)
    assert count >= 1
    assert any("Fix:" in msg.content for msg in new_for_zealot1)

    bridge.send_message(dev_channel_id, zealot_1_id, "Implemented fix. Tests passing.")
    messages = bridge.get_messages(dev_channel_id)
    assert len(messages) >= 4


def test_full_spawn_task_events_flow(test_space, default_agents):
    """Agent creation → task creation → events emission data flow."""
    agent_identity = default_agents["zealot"]
    assert agent_identity is not None
    assert isinstance(agent_identity, str)
    assert len(agent_identity) > 0

    agent = spawn.get_agent(agent_identity)
    assert agent is not None
    agent_id = agent.agent_id

    task = spawns.create_spawn(agent_id=agent_id, is_task=True)
    assert task is not None
    assert task.id is not None

    retrieved_task = spawns.get_spawn(task.id)
    assert retrieved_task is not None
    assert retrieved_task.agent_id == agent_id
    assert isinstance(retrieved_task.agent_id, str)

    spawns.update_status(task.id, "completed")
    updated_task = spawns.get_spawn(task.id)
    assert updated_task.status == "completed"
    assert updated_task.agent_id == agent_id


def test_pause_via_bridge_command(test_space, default_agents):
    """!identity pause command pauses running spawn."""
    dev_channel_id = bridge.create_channel("pause-test", "Testing pause")
    zealot_id = default_agents["zealot"]
    sentinel_id = default_agents["sentinel"]
    agent = spawn.get_agent(zealot_id)

    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task.id, TaskStatus.RUNNING)

    assert spawns.get_spawn(task.id).status == TaskStatus.RUNNING

    bridge.send_message(dev_channel_id, sentinel_id, f"!{zealot_id}")
    time.sleep(0.2)

    paused_task = spawns.get_spawn(task.id)
    assert paused_task.status == TaskStatus.PAUSED


def test_resume_via_bridge_mention_no_session(test_space, default_agents):
    """@identity mention without session_id cannot resume (requires session context)."""
    dev_channel_id = bridge.create_channel("resume-no-session", "Testing resume without session")
    zealot_id = default_agents["zealot"]
    sentinel_id = default_agents["sentinel"]
    agent = spawn.get_agent(zealot_id)

    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task.id, TaskStatus.PAUSED)

    assert spawns.get_spawn(task.id).status == TaskStatus.PAUSED

    bridge.send_message(dev_channel_id, sentinel_id, f"@{zealot_id} resume the task")
    time.sleep(0.2)

    paused_task = spawns.get_spawn(task.id)
    assert paused_task.status == TaskStatus.PAUSED


def test_bridge_pause_resume_round_trip(test_space, default_agents):
    """Pause and resume via bridge preserves status across agent."""
    dev_channel_id = bridge.create_channel("pause-resume-rt", "Testing pause/resume")
    zealot_id = default_agents["zealot"]
    sentinel_id = default_agents["sentinel"]
    agent = spawn.get_agent(zealot_id)

    task1 = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task1.id, TaskStatus.RUNNING)

    original = spawns.get_spawn(task1.id)
    assert original.status == TaskStatus.RUNNING

    bridge.send_message(dev_channel_id, sentinel_id, f"!{zealot_id}")
    time.sleep(0.2)

    paused = spawns.get_spawn(task1.id)
    assert paused.status == TaskStatus.PAUSED
