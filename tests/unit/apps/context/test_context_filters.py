import pytest


def test_collect_timeline_filters_by_identity_uuid_not_name(test_space):
    """Regression test: context filters should compare agent_id UUIDs, not names."""
    from space.apps.context.db import collect_timeline
    from space.os.memory import db as memory_db
    from space.os.spawn import db as spawn_db

    agent1 = spawn_db.ensure_agent("alice")
    agent2 = spawn_db.ensure_agent("bob")

    memory_db.add_entry(agent1, "test-topic", "alice's memory")
    memory_db.add_entry(agent2, "test-topic", "bob's memory")

    timeline_alice = collect_timeline("test-topic", "alice", all_agents=False)
    timeline_all = collect_timeline("test-topic", None, all_agents=True)

    alice_count = sum(1 for item in timeline_alice if "alice" in item.get("identity", "").lower())
    all_alice_count = sum(1 for item in timeline_all if "alice" in item.get("identity", "").lower())

    assert alice_count > 0, "Should find alice's entries when filtering by alice"
    assert all_alice_count > 0, "Should find alice's entries in all agents timeline"


def test_collect_current_state_filters_by_agent_id(test_space):
    """Regression test: current state should filter by resolved agent_id."""
    from space.apps.context.db import collect_current_state
    from space.os.memory import db as memory_db
    from space.os.spawn import db as spawn_db

    agent1 = spawn_db.ensure_agent("charlie")
    agent2 = spawn_db.ensure_agent("diana")

    memory_db.add_entry(agent1, "test-topic", "charlie's data for search")
    memory_db.add_entry(agent2, "test-topic", "diana's data for search")

    results_charlie = collect_current_state("search", "charlie", all_agents=False)

    assert len(results_charlie["memory"]) > 0
    assert all(
        "charlie" in entry.get("identity", "").lower() for entry in results_charlie["memory"]
    )

    results_all = collect_current_state("search", None, all_agents=True)
    assert len(results_all["memory"]) >= 2


def test_collect_timeline_invalid_identity_raises_error(test_space):
    """Test that invalid identity names raise clear errors."""
    from space.apps.context.db import collect_timeline

    with pytest.raises(ValueError, match="Agent .* not found"):
        collect_timeline("test-topic", "nonexistent-agent", all_agents=False)
