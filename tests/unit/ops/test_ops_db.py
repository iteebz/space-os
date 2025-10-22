"""Unit tests for ops database operations."""

import pytest


def test_create_task(test_space):
    """Test creating a task."""
    from space.ops import db

    task_id = db.create_task("Test task")
    assert task_id is not None

    task = db.get_task(task_id)
    assert task is not None
    assert task.description == "Test task"
    assert task.status == "open"
    assert task.parent_id is None
    assert task.assigned_to is None


def test_create_task_with_parent(test_space):
    """Test creating a task with parent."""
    from space.ops import db

    parent_id = db.create_task("Parent task")
    child_id = db.create_task("Child task", parent_id=parent_id)

    child = db.get_task(child_id)
    assert child.parent_id == parent_id


def test_create_task_with_channel(test_space):
    """Test creating a task with channel link."""
    from space.ops import db

    task_id = db.create_task("Task with channel", channel_id="channel-123")
    task = db.get_task(task_id)
    assert task.channel_id == "channel-123"


def test_list_tasks_empty(test_space):
    """Test listing tasks when none exist."""
    from space.ops import db

    tasks = db.list_tasks()
    assert tasks == []


def test_list_tasks(test_space):
    """Test listing tasks."""
    from space.ops import db

    task1_id = db.create_task("Task 1")
    task2_id = db.create_task("Task 2")

    tasks = db.list_tasks()
    assert len(tasks) == 2
    # Should contain both tasks
    task_ids = {t.task_id for t in tasks}
    assert task_ids == {task1_id, task2_id}


def test_list_tasks_by_status(test_space):
    """Test filtering tasks by status."""
    from space.ops import db

    task1_id = db.create_task("Open task")
    task2_id = db.create_task("Claimed task")
    db.claim_task(task2_id, "agent-1")

    open_tasks = db.list_tasks(status="open")
    assert len(open_tasks) == 1
    assert open_tasks[0].task_id == task1_id

    claimed_tasks = db.list_tasks(status="claimed")
    assert len(claimed_tasks) == 1
    assert claimed_tasks[0].task_id == task2_id


def test_list_tasks_by_assigned_to(test_space):
    """Test filtering tasks by assigned agent."""
    from space.ops import db

    task1_id = db.create_task("Task 1")
    task2_id = db.create_task("Task 2")
    db.claim_task(task1_id, "agent-1")
    db.claim_task(task2_id, "agent-2")

    agent1_tasks = db.list_tasks(assigned_to="agent-1")
    assert len(agent1_tasks) == 1
    assert agent1_tasks[0].task_id == task1_id


def test_list_tasks_by_parent(test_space):
    """Test filtering tasks by parent."""
    from space.ops import db

    parent_id = db.create_task("Parent")
    child1_id = db.create_task("Child 1", parent_id=parent_id)
    child2_id = db.create_task("Child 2", parent_id=parent_id)
    db.create_task("Orphan")

    children = db.list_tasks(parent_id=parent_id)
    assert len(children) == 2
    assert {t.task_id for t in children} == {child1_id, child2_id}


def test_list_root_tasks(test_space):
    """Test filtering for root tasks only."""
    from space.ops import db

    root1_id = db.create_task("Root 1")
    root2_id = db.create_task("Root 2")
    parent_id = db.create_task("Parent")
    db.create_task("Child", parent_id=parent_id)

    roots = db.list_tasks(parent_id="")
    assert len(roots) == 3
    assert {t.task_id for t in roots} == {root1_id, root2_id, parent_id}


def test_claim_task(test_space):
    """Test claiming a task."""
    from space.ops import db

    task_id = db.create_task("Task to claim")
    success = db.claim_task(task_id, "agent-1")

    assert success is True
    task = db.get_task(task_id)
    assert task.assigned_to == "agent-1"
    assert task.status == "claimed"


def test_claim_already_claimed_task(test_space):
    """Test claiming an already claimed task fails."""
    from space.ops import db

    task_id = db.create_task("Task to claim")
    db.claim_task(task_id, "agent-1")

    success = db.claim_task(task_id, "agent-2")
    assert success is False

    task = db.get_task(task_id)
    assert task.assigned_to == "agent-1"


def test_complete_task(test_space):
    """Test completing a task."""
    from space.ops import db

    task_id = db.create_task("Task to complete")
    db.claim_task(task_id, "agent-1")

    success = db.complete_task(task_id, "Work done", "agent-1")
    assert success is True

    task = db.get_task(task_id)
    assert task.status == "complete"
    assert task.handover == "Work done"
    assert task.completed_at is not None


def test_complete_task_wrong_agent(test_space):
    """Test completing a task assigned to different agent fails."""
    from space.ops import db

    task_id = db.create_task("Task to complete")
    db.claim_task(task_id, "agent-1")

    success = db.complete_task(task_id, "Work done", "agent-2")
    assert success is False

    task = db.get_task(task_id)
    assert task.status == "claimed"


def test_complete_blocked_task(test_space):
    """Test completing a blocked task."""
    from space.ops import db

    task_id = db.create_task("Task")
    db.claim_task(task_id, "agent-1")
    db.block_task(task_id, "Blocked reason")

    success = db.complete_task(task_id, "Unblocked and done", "agent-1")
    assert success is True

    task = db.get_task(task_id)
    assert task.status == "complete"


def test_block_task(test_space):
    """Test blocking a task."""
    from space.ops import db

    task_id = db.create_task("Task to block")
    success = db.block_task(task_id, "Needs clarification")

    assert success is True
    task = db.get_task(task_id)
    assert task.status == "blocked"
    assert task.handover == "Needs clarification"


def test_get_subtasks(test_space):
    """Test getting all subtasks."""
    from space.ops import db

    parent_id = db.create_task("Parent")
    child1_id = db.create_task("Child 1", parent_id=parent_id)
    child2_id = db.create_task("Child 2", parent_id=parent_id)

    subtasks = db.get_subtasks(parent_id)
    assert len(subtasks) == 2
    assert {t.task_id for t in subtasks} == {child1_id, child2_id}


def test_get_task_tree(test_space):
    """Test getting task tree structure."""
    from space.ops import db

    parent_id = db.create_task("Parent")
    child1_id = db.create_task("Child 1", parent_id=parent_id)
    child2_id = db.create_task("Child 2", parent_id=parent_id)
    grandchild_id = db.create_task("Grandchild", parent_id=child1_id)

    tree = db.get_task_tree(parent_id)
    assert tree is not None
    assert tree["task"].task_id == parent_id
    assert len(tree["subtasks"]) == 2

    # Find child1 in subtasks
    child1_tree = next(st for st in tree["subtasks"] if st["task"].task_id == child1_id)
    assert len(child1_tree["subtasks"]) == 1
    assert child1_tree["subtasks"][0]["task"].task_id == grandchild_id
