"""Spawn task lifecycle: creation, status transitions, agent/channel tracking."""

from unittest.mock import patch

from space.core.models import Agent, TaskStatus
from space.os import bridge, spawn


def test_create_task_with_channel(test_space, default_agents):
    """Task creation with channel stores both agent and channel references."""
    channel = bridge.create_channel("investigation-channel")
    zealot_id = default_agents["zealot"]

    task = spawn.create_task(identity=zealot_id, channel_id=channel.channel_id)

    assert task.channel_id == channel.channel_id
    assert task.agent_id is not None
    assert spawn.get_agent(task.agent_id).identity == zealot_id


def test_tasks_in_same_channel(test_space, default_agents):
    """Multiple tasks in same channel preserve individual agent references."""
    channel = bridge.create_channel("investigation-channel")

    t1 = spawn.create_task(identity=default_agents["zealot"], channel_id=channel.channel_id)
    t2 = spawn.create_task(identity=default_agents["sentinel"], channel_id=channel.channel_id)
    t3 = spawn.create_task(identity=default_agents["zealot"], channel_id=channel.channel_id)

    assert t1.channel_id == channel.channel_id
    assert t2.channel_id == channel.channel_id
    assert t3.channel_id == channel.channel_id

    assert spawn.get_agent(t1.agent_id).identity == default_agents["zealot"]
    assert spawn.get_agent(t2.agent_id).identity == default_agents["sentinel"]
    assert spawn.get_agent(t3.agent_id).identity == default_agents["zealot"]


def test_channel_isolation(test_space, default_agents):
    """Tasks from different channels are isolated."""
    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")

    t_a = spawn.create_task(identity=default_agents["zealot"], channel_id=channel_a.channel_id)
    t_b = spawn.create_task(identity=default_agents["sentinel"], channel_id=channel_b.channel_id)

    task_a = spawn.get_task(t_a.id)
    task_b = spawn.get_task(t_b.id)

    assert task_a.channel_id == channel_a.channel_id
    assert task_b.channel_id == channel_b.channel_id
    assert task_a.channel_id != task_b.channel_id


def test_task_status_transitions(test_space, default_agents):
    """Task status progresses: pending → running → completed."""
    zealot_id = default_agents["zealot"]
    task = spawn.create_task(identity=zealot_id)

    assert task.status == TaskStatus.PENDING

    spawn.start_task(task.id)
    running_task = spawn.get_task(task.id)
    assert running_task.status == TaskStatus.RUNNING

    spawn.complete_task(task.id)
    completed_task = spawn.get_task(task.id)
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.ended_at is not None


def test_task_failure(test_space, default_agents):
    """Task can transition from running to failed."""
    zealot_id = default_agents["zealot"]
    task = spawn.create_task(identity=zealot_id)

    spawn.start_task(task.id)
    spawn.fail_task(task.id)

    failed_task = spawn.get_task(task.id)
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.ended_at is not None


def test_task_with_pid(test_space, default_agents):
    """Task can store PID for lifecycle management."""
    zealot_id = default_agents["zealot"]
    task = spawn.create_task(identity=zealot_id)

    spawn.start_task(task.id, pid=12345)
    running_task = spawn.get_task(task.id)
    assert running_task.pid == 12345


def test_list_tasks_all(test_space, default_agents):
    """List all tasks returns all background task sessions."""
    zealot_id = default_agents["zealot"]
    t1 = spawn.create_task(identity=zealot_id)
    t2 = spawn.create_task(identity=zealot_id)

    all_tasks = spawn.list_tasks()
    task_ids = {t.id for t in all_tasks}
    assert t1.id in task_ids
    assert t2.id in task_ids


def test_list_tasks_by_status(test_space, default_agents):
    """List tasks can filter by status."""
    zealot_id = default_agents["zealot"]
    t1 = spawn.create_task(identity=zealot_id)
    t2 = spawn.create_task(identity=zealot_id)

    spawn.complete_task(t1.id)

    pending_tasks = spawn.list_tasks(status=TaskStatus.PENDING.value)
    completed_tasks = spawn.list_tasks(status=TaskStatus.COMPLETED.value)

    assert t1.id not in {t.id for t in pending_tasks}
    assert t2.id in {t.id for t in pending_tasks}
    assert t1.id in {t.id for t in completed_tasks}


def test_list_tasks_by_identity(test_space, default_agents):
    """List tasks can filter by agent identity."""
    zealot_id = default_agents["zealot"]
    sentinel_id = default_agents["sentinel"]

    t_z = spawn.create_task(identity=zealot_id)
    t_s = spawn.create_task(identity=sentinel_id)

    zealot_tasks = spawn.list_tasks(identity=zealot_id)
    sentinel_tasks = spawn.list_tasks(identity=sentinel_id)

    task_ids_z = {t.id for t in zealot_tasks}
    task_ids_s = {t.id for t in sentinel_tasks}

    assert t_z.id in task_ids_z
    assert t_z.id not in task_ids_s
    assert t_s.id in task_ids_s
    assert t_s.id not in task_ids_z


def test_list_tasks_by_channel(test_space, default_agents):
    """List tasks can filter by channel."""
    channel = bridge.create_channel("test-channel")
    zealot_id = default_agents["zealot"]

    t_in_channel = spawn.create_task(identity=zealot_id, channel_id=channel.channel_id)
    t_no_channel = spawn.create_task(identity=zealot_id)

    channel_tasks = spawn.list_tasks(channel_id=channel.channel_id)
    task_ids = {t.id for t in channel_tasks}

    assert t_in_channel.id in task_ids
    assert t_no_channel.id not in task_ids


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
        assert "SPACE-OS PROTOCOL" in result
        assert "question" in result
        assert "#subagents-test" in result
