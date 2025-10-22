"""Integration tests for ops API."""

import pytest


def test_create_and_get(test_space):
    """Test creating and retrieving a task via API."""
    from space.ops import api

    task_id = api.create("Test task")
    task = api.get(task_id)

    assert task is not None
    assert task.description == "Test task"
    assert task.status == "open"


def test_claim_and_complete_workflow(test_space):
    """Test full claim-complete workflow."""
    from space.ops import api
    from space.spawn import registry

    # Register agent
    agent_id = registry.ensure_agent("test-agent")

    # Create task
    task_id = api.create("Build feature")

    # Claim
    success = api.claim(task_id, agent_id)
    assert success is True

    # Complete
    success = api.complete(task_id, "Feature built. PR #123", agent_id)
    assert success is True

    # Verify
    task = api.get(task_id)
    assert task.status == "complete"
    assert task.handover == "Feature built. PR #123"


def test_reduce_aggregates_subtasks(test_space):
    """Test reduce aggregates completed subtasks."""
    from space.ops import api
    from space.spawn import registry

    agent1 = registry.ensure_agent("agent-1")
    agent2 = registry.ensure_agent("agent-2")
    integrator = registry.ensure_agent("integrator")

    # Create parent
    parent_id = api.create("Build payment system")

    # Create subtasks
    sub1_id = api.create("Stripe SDK", parent_id=parent_id)
    sub2_id = api.create("Webhooks", parent_id=parent_id)

    # Agents complete subtasks
    api.claim(sub1_id, agent1)
    api.complete(sub1_id, "SDK integrated", agent1)

    api.claim(sub2_id, agent2)
    api.complete(sub2_id, "Webhooks working", agent2)

    # Reduce
    success = api.reduce(parent_id, "Payment system complete", integrator)
    assert success is True

    # Verify parent
    parent = api.get(parent_id)
    assert parent.status == "complete"
    assert "Payment system complete" in parent.handover
    assert "SDK integrated" in parent.handover
    assert "Webhooks working" in parent.handover


def test_reduce_fails_with_incomplete_subtasks(test_space):
    """Test reduce fails if subtasks not all complete."""
    from space.ops import api
    from space.spawn import registry

    agent = registry.ensure_agent("agent")

    parent_id = api.create("Parent")
    sub1_id = api.create("Sub 1", parent_id=parent_id)
    sub2_id = api.create("Sub 2", parent_id=parent_id)

    # Only complete one subtask
    api.claim(sub1_id, agent)
    api.complete(sub1_id, "Done", agent)

    # Reduce should fail
    success = api.reduce(parent_id, "Integration", agent)
    assert success is False

    # Parent should still be open
    parent = api.get(parent_id)
    assert parent.status == "open"


def test_tree_shows_hierarchy(test_space):
    """Test tree API returns hierarchical structure."""
    from space.ops import api

    parent_id = api.create("Parent")
    child1_id = api.create("Child 1", parent_id=parent_id)
    child2_id = api.create("Child 2", parent_id=parent_id)

    tree = api.tree(parent_id)

    assert tree["task"].task_id == parent_id
    assert len(tree["subtasks"]) == 2

    subtask_ids = {st["task"].task_id for st in tree["subtasks"]}
    assert subtask_ids == {child1_id, child2_id}


def test_block_task_via_api(test_space):
    """Test blocking a task via API."""
    from space.ops import api

    task_id = api.create("Blocked task")
    success = api.block(task_id, "Waiting for dependencies")

    assert success is True
    task = api.get(task_id)
    assert task.status == "blocked"
    assert task.handover == "Waiting for dependencies"


def test_list_filters(test_space):
    """Test list with various filters."""
    from space.ops import api
    from space.spawn import registry

    agent1 = registry.ensure_agent("agent-1")
    agent2 = registry.ensure_agent("agent-2")

    # Create various tasks
    task1 = api.create("Open task 1")
    task2 = api.create("Open task 2")
    task3 = api.create("Claimed task")
    api.claim(task3, agent1)

    # Filter by status
    open_tasks = api.list_tasks(status="open")
    assert len(open_tasks) == 2

    claimed_tasks = api.list_tasks(status="claimed")
    assert len(claimed_tasks) == 1

    # Filter by agent
    agent1_tasks = api.list_tasks(assigned_to=agent1)
    assert len(agent1_tasks) == 1
    assert agent1_tasks[0].task_id == task3
