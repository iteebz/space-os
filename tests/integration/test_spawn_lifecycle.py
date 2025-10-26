from unittest.mock import MagicMock, patch

from space.core import bridge, spawn
from space.core.bridge.api import mentions


def test_channel_groups_tasks(test_space):
    """Tasks in same channel preserve agent references."""
    channel = bridge.create_channel("investigation-channel")
    spawn.ensure_agent("zealot")
    spawn.ensure_agent("sentinel")

    t1_id = spawn.create_task("zealot", "test", channel_id=channel.channel_id)
    t2_id = spawn.create_task("sentinel", "test", channel_id=channel.channel_id)
    t3_id = spawn.create_task("zealot", "test", channel_id=channel.channel_id)

    t1 = spawn.get_task(t1_id)
    t2 = spawn.get_task(t2_id)
    t3 = spawn.get_task(t3_id)

    assert t1.channel_id == channel.channel_id
    assert t2.channel_id == channel.channel_id
    assert t3.channel_id == channel.channel_id

    assert spawn.resolve_agent(t1.agent_id).identity == "zealot"
    assert spawn.resolve_agent(t2.agent_id).identity == "sentinel"
    assert spawn.resolve_agent(t3.agent_id).identity == "zealot"


def test_channel_isolation(test_space):
    """Tasks from different channels isolated."""
    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")
    spawn.ensure_agent("zealot")
    spawn.ensure_agent("sentinel")

    t_a = spawn.create_task("zealot", "test", channel_id=channel_a.channel_id)
    t_b = spawn.create_task("sentinel", "test", channel_id=channel_b.channel_id)

    task_a = spawn.get_task(t_a)
    task_b = spawn.get_task(t_b)

    assert task_a.channel_id == channel_a.channel_id
    assert task_b.channel_id == channel_b.channel_id
    assert task_a.channel_id != task_b.channel_id


def test_retrieve_channel_history(test_space):
    """Retrieve task history preserves agent and output."""
    channel = bridge.create_channel("investigation")
    spawn.ensure_agent("zealot")
    spawn.ensure_agent("sentinel")

    task_outputs = [
        ("zealot", "started investigation"),
        ("sentinel", "gathered data"),
        ("zealot", "final report"),
    ]

    task_ids = []
    for agent, output in task_outputs:
        t_id = spawn.create_task(agent, "test", channel_id=channel.channel_id)
        spawn.complete_task(t_id, output=output)
        task_ids.append(t_id)

    for task_id, (agent, output) in zip(task_ids, task_outputs, strict=False):
        task = spawn.get_task(task_id)
        assert spawn.resolve_agent(task.agent_id).identity == agent
        assert task.output == output


def test_spawn_logs_metadata(test_space):
    """Spawn task stores all metadata (agent, channel, output, status)."""
    channel = bridge.create_channel("subagents-test")
    spawn.ensure_agent("zealot")
    output = "response"

    task_id = spawn.create_task("zealot", "test", channel_id=channel.channel_id)
    spawn.complete_task(task_id, output=output)

    task = spawn.get_task(task_id)

    assert spawn.resolve_agent(task.agent_id).identity == "zealot"
    assert task.channel_id == channel.channel_id
    assert task.output == output
    assert task.status == "completed"


def test_mention_spawns_worker():
    """Bridge detects @mention and returns prompt for spawning."""
    with (
        patch("space.core.bridge.api.mentions.subprocess.run") as mock_run,
        patch("space.core.bridge.api.mentions.config.load_config") as mock_config,
    ):
        mock_config.return_value = {"roles": {"zealot": {}}}
        mock_run.return_value = MagicMock(
            returncode=0, stdout="# subagents-test\n\n[alice] hello\n"
        )

        result = mentions._build_prompt("zealot", "subagents-test", "@zealot question")

        assert result is not None
        assert "[SPACE INSTRUCTIONS]" in result


def test_task_provenance_chain(test_space):
    """Task entry tracks full provenance: agent_id, channel_id, output, status, timestamps."""
    channel = bridge.create_channel("investigation")
    spawn.ensure_agent("zealot")
    output = "findings"

    task_id = spawn.create_task("zealot", "test", channel_id=channel.channel_id)
    spawn.complete_task(task_id, output=output)

    task = spawn.get_task(task_id)

    assert task.task_id == task_id
    assert spawn.resolve_agent(task.agent_id).identity == "zealot"
    assert task.channel_id == channel.channel_id
    assert task.output == output
    assert task.status == "completed"
    assert task.created_at is not None
    assert task.completed_at is not None


def test_task_pending_to_running(test_space):
    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="list repos")

    task = spawn.get_task(task_id)
    assert task.status == "pending"
    spawn.start_task(task_id)
    task = spawn.get_task(task_id)
    assert task.status == "running"
    assert task.started_at is not None


def test_task_running_to_completed(test_space):
    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="list repos")
    spawn.start_task(task_id)

    output = "repo1\nrepo2\nrepo3"
    spawn.complete_task(task_id, output=output)

    task = spawn.get_task(task_id)
    assert task.status == "completed"
    assert task.output == output
    assert task.completed_at is not None
    assert task.duration is not None
    assert task.duration >= 0


def test_task_running_to_failed(test_space):
    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="run command")
    spawn.start_task(task_id)

    stderr = "command not found"
    spawn.fail_task(task_id, stderr=stderr)

    task = spawn.get_task(task_id)
    assert task.status == "failed"
    assert task.stderr == stderr
    assert task.output is None
    assert task.completed_at is not None


def test_task_pending_to_timeout(test_space):
    spawn.ensure_agent("zealot")
    task_id = spawn.create_task(role="zealot", input="slow task")

    spawn.fail_task(task_id)
    task = spawn.get_task(task_id)
    assert task.status == "failed"
    assert task.started_at is None
    assert task.completed_at is not None
