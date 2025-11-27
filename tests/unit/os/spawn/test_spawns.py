"""Spawn lifecycle tests."""

from unittest.mock import MagicMock, patch

from space.os.spawn.api import spawns


def test_update_status_syncs_session_on_terminal():
    """Update spawn status to terminal should trigger session index."""
    with patch("space.os.spawn.api.spawns.store.ensure") as mock_store:
        with patch("space.os.spawn.api.spawns.get_spawn") as mock_get_spawn:
            with patch("space.os.sessions.api.sync.index") as mock_index:
                mock_conn = MagicMock()
                mock_store.return_value.__enter__.return_value = mock_conn

                spawn_obj = MagicMock()
                spawn_obj.id = "spawn-123"
                spawn_obj.session_id = "sess-456"
                mock_get_spawn.return_value = spawn_obj

                spawns.update_status("spawn-123", "completed")

                mock_index.assert_called_once_with("sess-456")


def test_update_status_does_not_index_non_terminal():
    """Update spawn status to non-terminal should NOT index."""
    with patch("space.os.spawn.api.spawns.store.ensure") as mock_store:
        with patch("space.os.sessions.api.sync.index") as mock_index:
            mock_conn = MagicMock()
            mock_store.return_value.__enter__.return_value = mock_conn

            spawns.update_status("spawn-123", "running")

            mock_index.assert_not_called()


def test_update_status_syncs_on_failed():
    """Update spawn status to failed should trigger session index."""
    with patch("space.os.spawn.api.spawns.store.ensure") as mock_store:
        with patch("space.os.spawn.api.spawns.get_spawn") as mock_get_spawn:
            with patch("space.os.sessions.api.sync.index") as mock_index:
                mock_conn = MagicMock()
                mock_store.return_value.__enter__.return_value = mock_conn

                spawn_obj = MagicMock()
                spawn_obj.id = "spawn-123"
                spawn_obj.session_id = "sess-456"
                mock_get_spawn.return_value = spawn_obj

                spawns.update_status("spawn-123", "failed")

                mock_index.assert_called_once_with("sess-456")


def test_update_status_syncs_on_timeout():
    """Update spawn status to timeout should trigger session index."""
    with patch("space.os.spawn.api.spawns.store.ensure") as mock_store:
        with patch("space.os.spawn.api.spawns.get_spawn") as mock_get_spawn:
            with patch("space.os.sessions.api.sync.index") as mock_index:
                mock_conn = MagicMock()
                mock_store.return_value.__enter__.return_value = mock_conn

                spawn_obj = MagicMock()
                spawn_obj.id = "spawn-123"
                spawn_obj.session_id = "sess-456"
                mock_get_spawn.return_value = spawn_obj

                spawns.update_status("spawn-123", "timeout")

                mock_index.assert_called_once_with("sess-456")


def test_get_spawn_depth(test_space):
    """Contract: get_spawn_depth returns correct ancestor count."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root = spawns.create_spawn(agent.agent_id)
    child1 = spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(agent.agent_id, parent_spawn_id=child1.id)

    assert spawns.get_spawn_depth(root.id) == 0
    assert spawns.get_spawn_depth(child1.id) == 1
    assert spawns.get_spawn_depth(child2.id) == 2


def test_get_spawn_lineage(test_space):
    """Contract: get_spawn_lineage returns [spawn, parent, grandparent, ...]."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root = spawns.create_spawn(agent.agent_id)
    child1 = spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(agent.agent_id, parent_spawn_id=child1.id)

    lineage = spawns.get_spawn_lineage(child2.id)

    assert lineage == [child2.id, child1.id, root.id]


def test_get_spawn_children(test_space):
    """Contract: get_spawn_children returns direct children in creation order."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    parent = spawns.create_spawn(agent.agent_id)
    child1 = spawns.create_spawn(agent.agent_id, parent_spawn_id=parent.id)
    child2 = spawns.create_spawn(agent.agent_id, parent_spawn_id=parent.id)

    children = spawns.get_spawn_children(parent.id)

    assert len(children) == 2
    assert children[0].id == child1.id
    assert children[1].id == child2.id


def test_get_all_root_spawns(test_space):
    """Contract: get_all_root_spawns returns only spawns with no parent."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root1 = spawns.create_spawn(agent.agent_id)
    root2 = spawns.create_spawn(agent.agent_id)
    child = spawns.create_spawn(agent.agent_id, parent_spawn_id=root1.id)

    roots = spawns.get_all_root_spawns(limit=100)

    root_ids = [r.id for r in roots]
    assert root1.id in root_ids
    assert root2.id in root_ids
    assert child.id not in root_ids


def test_spawn_tree_hierarchy(test_space):
    """Contract: spawn tree hierarchies are correctly built."""
    from space.os.spawn.api import agents

    agents.register_agent("agent-a", "claude-haiku-4-5", None)
    agents.register_agent("agent-b", "claude-haiku-4-5", None)
    agent_a = agents.get_agent("agent-a")
    agent_b = agents.get_agent("agent-b")

    root = spawns.create_spawn(agent_a.agent_id)
    child1 = spawns.create_spawn(agent_a.agent_id, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(agent_b.agent_id, parent_spawn_id=root.id)
    grandchild = spawns.create_spawn(agent_a.agent_id, parent_spawn_id=child1.id)

    all_spawns = spawns.get_all_spawns(limit=500)
    children_map: dict[str, list[str]] = {}

    for spawn in all_spawns:
        if spawn.parent_spawn_id:
            if spawn.parent_spawn_id not in children_map:
                children_map[spawn.parent_spawn_id] = []
            children_map[spawn.parent_spawn_id].append(spawn.id)

    assert root.id in children_map
    assert len(children_map[root.id]) == 2
    assert child1.id in children_map[root.id]
    assert child2.id in children_map[root.id]
    assert child1.id in children_map
    assert grandchild.id in children_map[child1.id]


def test_spawn_tree_independent_roots(test_space):
    """Contract: multiple independent spawn trees remain separate."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root1 = spawns.create_spawn(agent.agent_id)
    child1 = spawns.create_spawn(agent.agent_id, parent_spawn_id=root1.id)

    root2 = spawns.create_spawn(agent.agent_id)
    child2 = spawns.create_spawn(agent.agent_id, parent_spawn_id=root2.id)

    roots = spawns.get_all_root_spawns()
    root_ids = [r.id for r in roots]
    assert root1.id in root_ids
    assert root2.id in root_ids

    root1_children = spawns.get_spawn_children(root1.id)
    root2_children = spawns.get_spawn_children(root2.id)

    assert len(root1_children) == 1
    assert root1_children[0].id == child1.id
    assert len(root2_children) == 1
    assert root2_children[0].id == child2.id


def test_get_spawn_children_empty(test_space):
    """Contract: get_spawn_children returns empty list for spawn with no children."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    spawn_obj = spawns.create_spawn(agent.agent_id)
    children = spawns.get_spawn_children(spawn_obj.id)

    assert children == []


def test_get_spawn_lineage_root_only(test_space):
    """Contract: get_spawn_lineage returns [spawn_id] for root spawn."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root = spawns.create_spawn(agent.agent_id)
    lineage = spawns.get_spawn_lineage(root.id)

    assert lineage == [root.id]


def test_get_all_root_spawns_empty(test_space):
    """Contract: get_all_root_spawns returns empty list if no roots exist."""
    roots = spawns.get_all_root_spawns()
    assert roots == []


def test_get_spawn_by_partial_id(test_space):
    """Contract: get_spawn matches by partial ID (LIKE pattern)."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    spawn_obj = spawns.create_spawn(agent.agent_id)
    partial_id = spawn_obj.id[:8]

    found = spawns.get_spawn(partial_id)
    assert found is not None
    assert found.id == spawn_obj.id


def test_get_spawn_by_full_id(test_space):
    """Contract: get_spawn matches by full ID."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    spawn_obj = spawns.create_spawn(agent.agent_id)
    found = spawns.get_spawn(spawn_obj.id)

    assert found is not None
    assert found.id == spawn_obj.id


def test_get_spawn_nonexistent_returns_none(test_space):
    """Contract: get_spawn returns None for nonexistent ID."""
    found = spawns.get_spawn("nonexistent-id-that-never-existed")
    assert found is None


def test_spawn_depth_exceeds_max(test_space):
    """Contract: get_spawn_lineage raises on circular reference (depth loop)."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root = spawns.create_spawn(agent.agent_id)
    child = spawns.create_spawn(agent.agent_id, parent_spawn_id=root.id)

    with spawns.store.ensure() as conn:
        conn.execute(
            "UPDATE spawns SET parent_spawn_id = ? WHERE id = ?",
            (child.id, root.id),
        )

    try:
        spawns.get_spawn_lineage(root.id)
        raise AssertionError("Should have raised RuntimeError for circular reference")
    except RuntimeError as e:
        assert "loop detected" in str(e)
