"""Integration tests for polling and dismissal."""

import uuid
import pytest

from space.os.core.bridge import db as bridge_db
from space.os.core.spawn import db as spawn_db
from space.apps import stats as stats_lib


@pytest.fixture
def setup_polling():
    """Create channel, agent, and poll."""
    channel_id = bridge_db.create_channel(f"test-polls-{uuid.uuid4().hex[:8]}")
    agent_id = spawn_db.ensure_agent(f"test-agent-{uuid.uuid4().hex[:8]}")
    poll_id = bridge_db.create_poll(agent_id, channel_id, created_by="human")
    return channel_id, agent_id, poll_id


def test_create_poll(setup_polling):
    """Test poll creation."""
    channel_id, agent_id, poll_id = setup_polling
    assert poll_id is not None
    polls = bridge_db.get_active_polls(channel_id)
    assert len(polls) == 1
    assert polls[0]["agent_id"] == agent_id
    assert polls[0]["channel_id"] == channel_id


def test_is_polling(setup_polling):
    """Test polling status check."""
    channel_id, agent_id, poll_id = setup_polling
    assert bridge_db.is_polling(agent_id, channel_id)


def test_dismiss_poll(setup_polling):
    """Test poll dismissal."""
    channel_id, agent_id, poll_id = setup_polling
    assert bridge_db.is_polling(agent_id, channel_id)
    
    dismissed = bridge_db.dismiss_poll(agent_id, channel_id)
    assert dismissed is True
    assert not bridge_db.is_polling(agent_id, channel_id)
    
    polls = bridge_db.get_active_polls(channel_id)
    assert len(polls) == 0


def test_active_polls_map_in_stats(setup_polling):
    """Test polling appears in agent stats."""
    channel_id, agent_id, poll_id = setup_polling
    
    stats = stats_lib.agent_stats()
    assert stats is not None
    
    test_agent = next((a for a in stats if a.agent_id == agent_id), None)
    assert test_agent is not None
    assert test_agent.active_polls is not None
    assert len(test_agent.active_polls) > 0
    
    channel_name = bridge_db.get_channel_name(channel_id)
    assert channel_name in test_agent.active_polls


def test_multiple_polls(setup_polling):
    """Test multiple active polls for same agent."""
    channel_id, agent_id, poll_id = setup_polling
    channel_id2 = bridge_db.create_channel(f"test-polls-2-{uuid.uuid4().hex[:8]}")
    poll_id2 = bridge_db.create_poll(agent_id, channel_id2, created_by="human")
    
    stats = stats_lib.agent_stats()
    test_agent = next((a for a in stats if a.agent_id == agent_id), None)
    assert test_agent is not None
    assert len(test_agent.active_polls) == 2
