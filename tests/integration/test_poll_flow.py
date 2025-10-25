"""End-to-end polling flow test."""

from unittest.mock import patch

from space.os.core.bridge import db, worker
from space.os.core.spawn import db as spawn_db


@patch("space.os.core.bridge.worker.config.init_config")
@patch("space.os.core.bridge.worker.config.load_config")
def test_poll_flow_create_and_dismiss(mock_config, mock_init, test_space):
    """Full polling flow: create poll, check status, dismiss."""
    mock_config.return_value = {"roles": {}}

    channel_id = db.resolve_channel_id("dev")
    channel_name = "dev"

    worker.main.__globals__["sys"].argv = [
        "worker",
        channel_id,
        channel_name,
        "/poll @hailot",
    ]

    agent_id = spawn_db.ensure_agent("hailot")

    db.create_poll(agent_id, channel_id, created_by="human")

    assert db.is_polling(agent_id, channel_id)

    polls = db.get_active_polls(channel_id=channel_id)
    assert len(polls) == 1
    assert polls[0]["agent_id"] == agent_id

    db.dismiss_poll(agent_id, channel_id)
    assert not db.is_polling(agent_id, channel_id)

    polls = db.get_active_polls(channel_id=channel_id)
    assert len(polls) == 0


def test_poll_status_in_stats(test_space):
    """Active polls show in agent stats."""
    from space.apps import stats

    agent_id = spawn_db.ensure_agent("hailot")
    channel_id = db.resolve_channel_id("dev")
    channel_name = db.get_channel_name(channel_id)

    db.create_poll(agent_id, channel_id, created_by="human")

    agent_list = stats.agent_stats()
    hailot = next((a for a in agent_list if a.agent_name == "hailot"), None)

    assert hailot is not None
    assert hailot.active_polls is not None
    assert channel_name in hailot.active_polls
