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

    root = spawns.create_spawn(agent.agent_id, is_ephemeral=True)
    child1 = spawns.create_spawn(agent.agent_id, is_ephemeral=True, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(agent.agent_id, is_ephemeral=True, parent_spawn_id=child1.id)

    assert spawns.get_spawn_depth(root.id) == 0
    assert spawns.get_spawn_depth(child1.id) == 1
    assert spawns.get_spawn_depth(child2.id) == 2


def test_get_spawn_lineage(test_space):
    """Contract: get_spawn_lineage returns [spawn, parent, grandparent, ...]."""
    from space.os.spawn.api import agents

    agents.register_agent("test-agent", "claude-haiku-4-5", None)
    agent = agents.get_agent("test-agent")

    root = spawns.create_spawn(agent.agent_id, is_ephemeral=True)
    child1 = spawns.create_spawn(agent.agent_id, is_ephemeral=True, parent_spawn_id=root.id)
    child2 = spawns.create_spawn(agent.agent_id, is_ephemeral=True, parent_spawn_id=child1.id)

    lineage = spawns.get_spawn_lineage(child2.id)

    assert lineage == [child2.id, child1.id, root.id]
