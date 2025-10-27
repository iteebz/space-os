from space.os import bridge, spawn


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


def test_agent_bookmark_isolation(test_space, default_agents):
    """Each agent maintains independent bookmark; doesn't see other reads."""
    channel_id = bridge.create_channel("shared-channel")
    zealot_1_id = default_agents["zealot"]
    zealot_2_id = default_agents["sentinel"]

    bridge.send_message(channel_id, "zealot", "message 1")

    new_z1, count_z1, _, _ = bridge.recv_messages(channel_id, zealot_1_id)
    assert count_z1 == 1

    bridge.send_message(channel_id, "zealot", "message 2")

    new_z2, count_z2, _, _ = bridge.recv_messages(channel_id, zealot_2_id)
    assert count_z2 == 2

    new_z1_again, count_z1_again, _, _ = bridge.recv_messages(channel_id, zealot_1_id)
    assert count_z1_again == 1

    bridge.send_message(channel_id, "zealot", "message 3")

    new_z1_final, count_z1_final, _, _ = bridge.recv_messages(channel_id, zealot_1_id)
    assert count_z1_final == 1
    assert "message 3" in new_z1_final[0].content

    new_z2_final, count_z2_final, _, _ = bridge.recv_messages(channel_id, zealot_2_id)
    assert count_z2_final == 1
    assert "message 3" in new_z2_final[0].content


def test_full_spawn_task_events_flow(test_space, default_agents):
    """Agent creation → task creation → events emission data flow."""
    agent_identity = default_agents["zealot"]
    assert agent_identity is not None
    assert isinstance(agent_identity, str)
    assert len(agent_identity) > 0

    # Get the actual agent object to get the real agent_id (UUID)
    agent = spawn.get_agent(agent_identity)
    assert agent is not None
    agent_id = agent.agent_id

    task_id = spawn.create_task(agent_identity, "test input")
    assert task_id is not None

    task = spawn.get_task(task_id)
    assert task is not None
    assert task.agent_id == agent_id
    assert isinstance(task.agent_id, str)

    spawn.complete_task(task_id, output="test output")
    updated_task = spawn.get_task(task_id)
    assert updated_task.status == "completed"
    assert updated_task.agent_id == agent_id
