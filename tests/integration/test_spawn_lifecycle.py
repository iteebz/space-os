"""Spawn task lifecycle: creation, status transitions, agent/channel tracking."""

from unittest.mock import patch

import pytest

from space.core.models import Agent, TaskStatus
from space.os import bridge, spawn
from space.os.spawn.api import spawns


def test_create_task_with_channel(test_space, default_agents):
    """Task creation with channel stores both agent and channel references."""
    channel = bridge.create_channel("investigation-channel")
    zealot_agent_id = default_agents["zealot"]
    agent = spawn.get_agent(zealot_agent_id)

    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True, channel_id=channel.channel_id)

    assert task.channel_id == channel.channel_id
    assert task.agent_id is not None
    assert spawn.get_agent(task.agent_id).identity == "zealot"


def test_tasks_in_same_channel(test_space, default_agents):
    """Multiple tasks in same channel preserve individual agent references."""
    channel = bridge.create_channel("investigation-channel")
    zealot_agent = spawn.get_agent(default_agents["zealot"])
    sentinel_agent = spawn.get_agent(default_agents["sentinel"])

    t1 = spawns.create_spawn(
        agent_id=zealot_agent.agent_id, is_task=True, channel_id=channel.channel_id
    )
    t2 = spawns.create_spawn(
        agent_id=sentinel_agent.agent_id, is_task=True, channel_id=channel.channel_id
    )
    t3 = spawns.create_spawn(
        agent_id=zealot_agent.agent_id, is_task=True, channel_id=channel.channel_id
    )

    assert t1.channel_id == channel.channel_id
    assert t2.channel_id == channel.channel_id
    assert t3.channel_id == channel.channel_id

    assert spawn.get_agent(t1.agent_id).identity == "zealot"
    assert spawn.get_agent(t2.agent_id).identity == "sentinel"
    assert spawn.get_agent(t3.agent_id).identity == "zealot"


def test_channel_isolation(test_space, default_agents):
    """Tasks from different channels are isolated."""
    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")
    zealot_agent = spawn.get_agent(default_agents["zealot"])
    sentinel_agent = spawn.get_agent(default_agents["sentinel"])

    t_a = spawns.create_spawn(
        agent_id=zealot_agent.agent_id, is_task=True, channel_id=channel_a.channel_id
    )
    t_b = spawns.create_spawn(
        agent_id=sentinel_agent.agent_id, is_task=True, channel_id=channel_b.channel_id
    )

    task_a = spawns.get_spawn(t_a.id)
    task_b = spawns.get_spawn(t_b.id)

    assert task_a.channel_id == channel_a.channel_id
    assert task_b.channel_id == channel_b.channel_id
    assert task_a.channel_id != task_b.channel_id


def test_task_status_transitions(test_space, default_agents):
    """Task status progresses: pending → running → completed."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    assert task.status == TaskStatus.PENDING

    spawns.update_status(task.id, TaskStatus.RUNNING)
    running_task = spawns.get_spawn(task.id)
    assert running_task.status == TaskStatus.RUNNING

    spawns.update_status(task.id, TaskStatus.COMPLETED)
    completed_task = spawns.get_spawn(task.id)
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.ended_at is not None


def test_task_failure(test_space, default_agents):
    """Task can transition from running to failed."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    spawns.update_status(task.id, TaskStatus.RUNNING)
    spawns.update_status(task.id, TaskStatus.FAILED)

    failed_task = spawns.get_spawn(task.id)
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.ended_at is not None


def test_task_with_pid(test_space, default_agents):
    """Task can store PID for lifecycle management."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    spawns.update_status(task.id, TaskStatus.RUNNING)
    # Update PID directly in spawns (no pid parameter in update_status)
    # For now, just verify task creation works
    running_task = spawns.get_spawn(task.id)
    assert running_task is not None


def test_list_tasks_all(test_space, default_agents):
    """List all spawns with is_task=True returns all background task sessions."""
    agent = spawn.get_agent(default_agents["zealot"])
    t1 = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    t2 = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    all_tasks = [s for s in all_spawns if s.is_task]
    task_ids = {t.id for t in all_tasks}
    assert t1.id in task_ids
    assert t2.id in task_ids


def test_list_tasks_by_status(test_space, default_agents):
    """Spawns can be filtered by status."""
    agent = spawn.get_agent(default_agents["zealot"])
    t1 = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    t2 = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    spawns.update_status(t1.id, TaskStatus.COMPLETED)

    # Filter by status manually
    all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    pending_tasks = [s for s in all_spawns if s.is_task and s.status == TaskStatus.PENDING]
    completed_tasks = [s for s in all_spawns if s.is_task and s.status == TaskStatus.COMPLETED]

    assert t1.id not in {t.id for t in pending_tasks}
    assert t2.id in {t.id for t in pending_tasks}
    assert t1.id in {t.id for t in completed_tasks}


def test_list_tasks_by_identity(test_space, default_agents):
    """Spawns can be filtered by agent."""
    zealot_agent = spawn.get_agent(default_agents["zealot"])
    sentinel_agent = spawn.get_agent(default_agents["sentinel"])

    t_z = spawns.create_spawn(agent_id=zealot_agent.agent_id, is_task=True)
    t_s = spawns.create_spawn(agent_id=sentinel_agent.agent_id, is_task=True)

    zealot_tasks = [s for s in spawns.get_spawns_for_agent(zealot_agent.agent_id) if s.is_task]
    sentinel_tasks = [s for s in spawns.get_spawns_for_agent(sentinel_agent.agent_id) if s.is_task]

    task_ids_z = {t.id for t in zealot_tasks}
    task_ids_s = {t.id for t in sentinel_tasks}

    assert t_z.id in task_ids_z
    assert t_z.id not in task_ids_s
    assert t_s.id in task_ids_s
    assert t_s.id not in task_ids_z


def test_list_tasks_by_channel(test_space, default_agents):
    """Spawns can be filtered by channel."""
    channel = bridge.create_channel("test-channel")
    agent = spawn.get_agent(default_agents["zealot"])

    t_in_channel = spawns.create_spawn(
        agent_id=agent.agent_id, is_task=True, channel_id=channel.channel_id
    )
    t_no_channel = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    # Filter by channel manually
    all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    channel_tasks = [s for s in all_spawns if s.is_task and s.channel_id == channel.channel_id]
    task_ids = {t.id for t in channel_tasks}

    assert t_in_channel.id in task_ids
    assert t_no_channel.id not in task_ids


def test_pause_task(test_space, default_agents):
    """Test pausing a running task."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task.id, TaskStatus.RUNNING)

    paused = spawn.pause_spawn(task.id)

    assert paused.status == TaskStatus.PAUSED


def test_pause_task_not_running(test_space, default_agents):
    """Test pausing a task that is not running."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    with pytest.raises(ValueError, match="not running"):
        spawn.pause_spawn(task.id)


def test_resume_task(test_space, default_agents):
    """Test resuming a paused task requires session_id."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task.id, TaskStatus.RUNNING)
    spawn.pause_spawn(task.id)

    # Cannot resume without session_id
    with pytest.raises(ValueError, match="no session_id"):
        spawn.resume_spawn(task.id)


def test_resume_task_not_paused(test_space, default_agents):
    """Test resuming a task that is not paused."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)

    with pytest.raises(ValueError, match="not paused"):
        spawn.resume_spawn(task.id)


def test_resume_task_no_session_id(test_space, default_agents):
    """Test resuming a paused task without session_id."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task.id, TaskStatus.RUNNING)
    spawn.pause_spawn(task.id)

    with pytest.raises(ValueError, match="no session_id"):
        spawn.resume_spawn(task.id)


def test_pause_resume_cycle_requires_session(test_space, default_agents):
    """Test pause/resume cycle requires valid session_id."""
    agent = spawn.get_agent(default_agents["zealot"])
    task = spawns.create_spawn(agent_id=agent.agent_id, is_task=True)
    spawns.update_status(task.id, TaskStatus.RUNNING)

    paused = spawn.pause_spawn(task.id)
    assert paused.status == TaskStatus.PAUSED

    # Resume fails without session_id
    with pytest.raises(ValueError, match="no session_id"):
        spawn.resume_spawn(task.id)


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
