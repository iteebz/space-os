from space.os import spawn


def test_list_tasks(test_space, default_agents):
    zealot_id = default_agents["zealot"]
    sentinel_id = default_agents["sentinel"]

    t1 = spawn.create_task(role=zealot_id, input="task 1")
    t2 = spawn.create_task(role=sentinel_id, input="task 2")
    spawn.complete_task(t1)

    all_tasks = spawn.list_tasks()
    assert len(all_tasks) == 2

    pending = spawn.list_tasks(status="pending")
    assert len(pending) == 1
    assert pending[0].task_id == t2

    zealot_tasks = spawn.list_tasks(role=zealot_id)
    assert len(zealot_tasks) == 1
    assert zealot_tasks[0].task_id == t1

    channel_id = "ch-spawn-test-123"
    task_id = spawn.create_task(
        role=zealot_id,
        input="list repos",
        channel_id=channel_id,
    )

    task = spawn.get_task(task_id)
    assert task.channel_id == channel_id

    spawn.start_task(task_id)
    spawn.complete_task(task_id, output="done")

    task = spawn.get_task(task_id)
    assert task.channel_id == channel_id
    assert task.status == "completed"


def test_multiple_tasks_per_identity(test_space, default_agents):
    zealot_id = default_agents["zealot"]

    t1 = spawn.create_task(role=zealot_id, input="task 1")
    t2 = spawn.create_task(role=zealot_id, input="task 2")
    t3 = spawn.create_task(role=zealot_id, input="task 3")

    spawn.start_task(t1)
    spawn.start_task(t2)
    zealot_tasks = spawn.list_tasks(role=zealot_id)
    assert len(zealot_tasks) == 3

    running = spawn.list_tasks(status="running", role=zealot_id)
    assert len(running) == 2
    assert {t.task_id for t in running} == {t1, t2}

    pending = spawn.list_tasks(status="pending", role=zealot_id)
    assert len(pending) == 1
    assert pending[0].task_id == t3
