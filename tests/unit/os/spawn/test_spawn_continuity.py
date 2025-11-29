"""Contract tests for spawn continuity: same spawn_id across @mentions."""

from space.core.models import SpawnStatus
from space.os.spawn.api import spawns


def test_get_active_spawn_in_channel_finds_active(test_space, default_agents):
    """get_active_spawn_in_channel returns spawn with status='active'."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    channel = bridge.create_channel("test-active")

    spawn = spawns.create_spawn(agent_id=zealot, channel_id=channel.channel_id)
    spawns.update_status(spawn.id, "active")

    found = spawns.get_active_spawn_in_channel(zealot, channel.channel_id)
    assert found is not None
    assert found.id == spawn.id
    assert found.status == SpawnStatus.ACTIVE


def test_get_active_spawn_in_channel_finds_running(test_space, default_agents):
    """get_active_spawn_in_channel returns spawn with status='running'."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    channel = bridge.create_channel("test-running")

    spawn = spawns.create_spawn(agent_id=zealot, channel_id=channel.channel_id)
    spawns.update_status(spawn.id, "running")

    found = spawns.get_active_spawn_in_channel(zealot, channel.channel_id)
    assert found is not None
    assert found.id == spawn.id
    assert found.status == SpawnStatus.RUNNING


def test_get_active_spawn_in_channel_ignores_completed(test_space, default_agents):
    """get_active_spawn_in_channel ignores completed spawns."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    channel = bridge.create_channel("test-completed")

    spawn = spawns.create_spawn(agent_id=zealot, channel_id=channel.channel_id)
    spawns.update_status(spawn.id, "completed")

    found = spawns.get_active_spawn_in_channel(zealot, channel.channel_id)
    assert found is None


def test_get_active_spawn_channel_isolation(test_space, default_agents):
    """Active spawns are isolated per channel."""
    from space.os import bridge

    zealot = default_agents["zealot"]
    channel_a = bridge.create_channel("channel-a")
    channel_b = bridge.create_channel("channel-b")

    spawn_a = spawns.create_spawn(agent_id=zealot, channel_id=channel_a.channel_id)
    spawns.update_status(spawn_a.id, "active")

    spawn_b = spawns.create_spawn(agent_id=zealot, channel_id=channel_b.channel_id)
    spawns.update_status(spawn_b.id, "active")

    found_a = spawns.get_active_spawn_in_channel(zealot, channel_a.channel_id)
    found_b = spawns.get_active_spawn_in_channel(zealot, channel_b.channel_id)

    assert found_a.id == spawn_a.id
    assert found_b.id == spawn_b.id
    assert found_a.id != found_b.id


def test_active_status_syncs_session(test_space, default_agents, mocker):
    """Transitioning to 'active' syncs session without finalizing."""
    zealot = default_agents["zealot"]

    spawn = spawns.create_spawn(agent_id=zealot)
    spawns.link_session_to_spawn(spawn.id, "test-session")

    mock_ingest = mocker.patch("space.os.sessions.api.sync.ingest")
    mock_index = mocker.patch("space.os.sessions.api.sync.index")

    spawns.update_status(spawn.id, "active")

    mock_ingest.assert_called_once_with("test-session")
    mock_index.assert_not_called()


def test_completed_status_finalizes_session(test_space, default_agents, mocker):
    """Transitioning to 'completed' syncs AND indexes session."""
    zealot = default_agents["zealot"]

    spawn = spawns.create_spawn(agent_id=zealot)
    spawns.link_session_to_spawn(spawn.id, "test-session")

    mock_ingest = mocker.patch("space.os.sessions.api.sync.ingest")
    mock_index = mocker.patch("space.os.sessions.api.sync.index")

    spawns.update_status(spawn.id, "completed")

    mock_ingest.assert_called_once_with("test-session")
    mock_index.assert_called_once_with("test-session")


def test_spawn_lifecycle_state_machine(test_space, default_agents):
    """Spawn follows: pending → running → active → running → active → completed."""
    zealot = default_agents["zealot"]

    spawn = spawns.create_spawn(agent_id=zealot)
    assert spawn.status == SpawnStatus.PENDING

    spawns.update_status(spawn.id, "running")
    spawn = spawns.get_spawn(spawn.id)
    assert spawn.status == SpawnStatus.RUNNING

    spawns.update_status(spawn.id, "active")
    spawn = spawns.get_spawn(spawn.id)
    assert spawn.status == SpawnStatus.ACTIVE

    spawns.update_status(spawn.id, "running")
    spawn = spawns.get_spawn(spawn.id)
    assert spawn.status == SpawnStatus.RUNNING

    spawns.update_status(spawn.id, "active")
    spawn = spawns.get_spawn(spawn.id)
    assert spawn.status == SpawnStatus.ACTIVE

    spawns.update_status(spawn.id, "completed")
    spawn = spawns.get_spawn(spawn.id)
    assert spawn.status == SpawnStatus.COMPLETED
    assert spawn.ended_at is not None


def test_terminate_spawn_running_kills(test_space, default_agents, mocker):
    """terminate_spawn kills running spawns."""
    zealot = default_agents["zealot"]

    spawn = spawns.create_spawn(agent_id=zealot)
    spawns.update_status(spawn.id, "running")

    mock_kill = mocker.patch.object(spawns, "kill_spawn")

    spawns.terminate_spawn(spawn.id, "completed")

    mock_kill.assert_called_once_with(spawn.id)


def test_terminate_spawn_active_sets_status(test_space, default_agents, mocker):
    """terminate_spawn sets final status for non-running spawns."""
    zealot = default_agents["zealot"]

    spawn = spawns.create_spawn(agent_id=zealot)
    spawns.update_status(spawn.id, "active")

    mocker.patch("space.os.sessions.api.sync.ingest")
    mocker.patch("space.os.sessions.api.sync.index")

    spawns.terminate_spawn(spawn.id, "completed")

    spawn = spawns.get_spawn(spawn.id)
    assert spawn.status == SpawnStatus.COMPLETED
