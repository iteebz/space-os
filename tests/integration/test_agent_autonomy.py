"""Test autonomous agent flow: agents post to bridge mid-execution."""

from space.bridge import api


def test_agent_posts_to_bridge_mid_execution(test_space):
    """Scenario: zealot-1 runs, hits decision point, posts to bridge for zealot-2 input."""
    # Setup
    dev_channel_id = api.create_channel("space-dev", "Development coordination")
    zealot_1_id = "zealot-1"
    zealot_2_id = "zealot-2"

    # Agent zealot-1 starts work
    agent_z1_uuid = api.send_message(
        dev_channel_id, zealot_1_id, "Starting analysis of spawn.py:42"
    )
    messages = api.fetch_messages(dev_channel_id)
    assert len(messages) == 1
    assert messages[0].agent_id == agent_z1_uuid

    # zealot-1 hits decision point mid-execution, posts autonomously
    api.send_message(
        dev_channel_id,
        zealot_1_id,
        "Found potential bug at line 42. @zealot-2 please review before merge",
    )
    messages = api.fetch_messages(dev_channel_id)
    # Note: @mention triggers worker spawn, adds system message
    assert len(messages) >= 2
    assert "@zealot-2" in messages[1].content

    # zealot-1 sleeps (execution pauses)
    # Detective reads bridge to see blocking state

    # zealot-2 wakes, reads new messages (includes system spawn message)
    new_for_zealot2, count, _, participants = api.recv_updates(dev_channel_id, zealot_2_id)
    assert count >= 2
    assert any("bug" in msg.content for msg in new_for_zealot2)

    # zealot-2 responds autonomously
    api.send_message(
        dev_channel_id,
        zealot_2_id,
        "Reviewed. Bug confirmed. Fix: change line 42 to `if x is None:`",
    )
    messages = api.fetch_messages(dev_channel_id)
    assert len(messages) >= 3
    assert any("Fix:" in msg.content for msg in messages)

    # zealot-1 wakes, reads response
    new_for_zealot1, count, _, _ = api.recv_updates(dev_channel_id, zealot_1_id)
    assert count >= 1
    assert any("Fix:" in msg.content for msg in new_for_zealot1)

    # zealot-1 continues execution with zealot-2's suggestion
    api.send_message(dev_channel_id, zealot_1_id, "Implemented fix. Tests passing.")
    messages = api.fetch_messages(dev_channel_id)
    assert len(messages) >= 4


def test_agent_loop_with_priority_blocking(test_space):
    """Scenario: zealot-1 raises alert, zealot-2 must respond before zealot-1 continues."""
    channel_id = api.create_channel("critical-path")
    zealot_1_id = "zealot-1"
    zealot_2_id = "zealot-2"

    # zealot-1 encounters blocker, raises alert
    api.send_message(
        channel_id,
        zealot_1_id,
        "Database migration needed. Blocking other tasks.",
        priority="alert",
    )

    # Detective or zealot-2 can see alerts
    alerts = api.get_alerts(zealot_2_id)
    assert len(alerts) >= 1
    assert any("Database migration" in msg.content for msg in alerts)

    # zealot-2 receives and responds
    api.send_message(channel_id, zealot_2_id, "Migration completed. Safe to proceed.")

    # zealot-1 reads bridge, sees response, continues
    new_msgs, count, _, _ = api.recv_updates(channel_id, zealot_1_id)
    assert count >= 1
    assert any("completed" in msg.content for msg in new_msgs)


def test_agent_coordination_multi_channel(test_space):
    """Scenario: agents coordinate across multiple channels simultaneously."""
    dev_channel = api.create_channel("space-dev")
    research_channel = api.create_channel("research")
    zealot_1_id = "zealot-1"
    zealot_2_id = "zealot-2"

    # zealot-1 posts in dev channel
    api.send_message(dev_channel, zealot_1_id, "Design complete. Ready for code review.")

    # zealot-1 also posts in research channel
    api.send_message(research_channel, zealot_1_id, "Found interesting pattern in coordination.")

    # zealot-2 reads from dev channel
    dev_new, dev_count, _, _ = api.recv_updates(dev_channel, zealot_2_id)
    assert dev_count >= 1

    # zealot-2 reads from research channel
    research_new, research_count, _, _ = api.recv_updates(research_channel, zealot_2_id)
    assert research_count >= 1

    # zealot-2 responds in dev channel
    api.send_message(dev_channel, zealot_2_id, "Code review approved.")

    # zealot-2 responds in research channel
    api.send_message(research_channel, zealot_2_id, "Great insight. Building on this.")

    # Verify both channels have correct conversation threads
    all_dev = api.fetch_messages(dev_channel)
    all_research = api.fetch_messages(research_channel)
    assert len(all_dev) == 2
    assert len(all_research) == 2


def test_agent_loop_bookmark_isolation(test_space):
    """Scenario: each agent maintains independent bookmark, doesn't see others' reads."""
    channel_id = api.create_channel("shared-channel")
    zealot_1_id = "zealot-1"
    zealot_2_id = "zealot-2"

    # Message 1 posted
    api.send_message(channel_id, "system", "message 1")

    # zealot-1 reads it
    new_z1, count_z1, _, _ = api.recv_updates(channel_id, zealot_1_id)
    assert count_z1 == 1

    # Message 2 posted
    api.send_message(channel_id, "system", "message 2")

    # zealot-2 hasn't read anything yet, should see both
    new_z2, count_z2, _, _ = api.recv_updates(channel_id, zealot_2_id)
    assert count_z2 == 2

    # zealot-1 reads message 2
    new_z1_again, count_z1_again, _, _ = api.recv_updates(channel_id, zealot_1_id)
    assert count_z1_again == 1

    # Message 3 posted
    api.send_message(channel_id, "system", "message 3")

    # zealot-1 sees only message 3
    new_z1_final, count_z1_final, _, _ = api.recv_updates(channel_id, zealot_1_id)
    assert count_z1_final == 1
    assert "message 3" in new_z1_final[0].content

    # zealot-2 sees only message 3 (already read 1 & 2)
    new_z2_final, count_z2_final, _, _ = api.recv_updates(channel_id, zealot_2_id)
    assert count_z2_final == 1
    assert "message 3" in new_z2_final[0].content
