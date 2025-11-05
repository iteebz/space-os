"""Task operations: core contracts and boundaries."""

import pytest

from space.os.task import api


def test_add_task_creates_open(test_space, default_agents):
    """Contract: add_task creates with open status, creator_id."""
    creator_id = default_agents["zealot"]
    task_id = api.add_task("Research X", creator_id=creator_id)

    task = api.get_task(task_id)
    assert task.status == "open"
    assert task.creator_id == creator_id
    assert task.agent_id is None


def test_list_tasks_filters_status(test_space, default_agents):
    """Contract: list_tasks respects status filtering."""
    creator_id = default_agents["zealot"]
    agent_id = default_agents["sentinel"]

    t1 = api.add_task("T1", creator_id=creator_id)
    api.add_task("T2", creator_id=creator_id)

    api.start_task(t1, agent_id)
    api.done_task(t1, agent_id)

    assert len(api.list_tasks(status="done")) == 1
    assert len(api.list_tasks(status="open")) == 1
    assert len(api.list_tasks()) == 1  # default: open + in_progress


def test_start_task_claims(test_space, default_agents):
    """Contract: start_task marks in_progress, sets agent_id."""
    creator_id = default_agents["zealot"]
    agent_id = default_agents["sentinel"]

    task_id = api.add_task("Task", creator_id=creator_id)
    api.start_task(task_id, agent_id)

    task = api.get_task(task_id)
    assert task.status == "in_progress"
    assert task.agent_id == agent_id
    assert task.started_at is not None


def test_remove_claim_unclaims(test_space, default_agents):
    """Contract: remove_claim returns to open, clears agent."""
    creator_id = default_agents["zealot"]
    agent_id = default_agents["sentinel"]

    task_id = api.add_task("Task", creator_id=creator_id)
    api.start_task(task_id, agent_id)
    api.remove_claim(task_id, agent_id)

    task = api.get_task(task_id)
    assert task.status == "open"
    assert task.agent_id is None


def test_done_task_completes(test_space, default_agents):
    """Contract: done_task marks complete, sets timestamp."""
    creator_id = default_agents["zealot"]
    agent_id = default_agents["sentinel"]

    task_id = api.add_task("Task", creator_id=creator_id)
    api.start_task(task_id, agent_id)
    api.done_task(task_id, agent_id)

    task = api.get_task(task_id)
    assert task.status == "done"
    assert task.completed_at is not None


def test_remove_claim_wrong_agent_raises(test_space, default_agents):
    """Boundary: remove_claim by non-owner raises."""
    creator_id = default_agents["zealot"]
    agent1 = default_agents["sentinel"]
    agent2 = default_agents["crucible"]

    task_id = api.add_task("Task", creator_id=creator_id)
    api.start_task(task_id, agent1)

    with pytest.raises(ValueError, match="not claimed by"):
        api.remove_claim(task_id, agent2)


def test_get_task_partial_id(test_space, default_agents):
    """Contract: get_task resolves partial IDs."""
    creator_id = default_agents["zealot"]
    task_id = api.add_task("Task", creator_id=creator_id)

    task = api.get_task(task_id[-8:])
    assert task.task_id == task_id
