"""Council test fixtures."""

from unittest.mock import Mock

import pytest

from space.apps.council.app import Council
from space.os.bridge import api, db


@pytest.fixture
def mock_channel():
    """Mock channel setup."""
    return {
        "channel_id": "test-channel-123",
        "channel_name": "test-council",
        "topic": "Testing coordination",
    }


@pytest.fixture
def mock_messages():
    """Mock message objects."""
    msg1 = Mock()
    msg1.message_id = "msg-1"
    msg1.agent_id = "agent-1"
    msg1.content = "First message"
    msg1.created_at = "2025-10-24T10:00:00"

    msg2 = Mock()
    msg2.message_id = "msg-2"
    msg2.agent_id = "agent-2"
    msg2.content = "Second message"
    msg2.created_at = "2025-10-24T10:05:00"

    return [msg1, msg2]


@pytest.fixture
def council_instance(mock_channel, monkeypatch):
    """Create a Council instance with mocked dependencies."""
    monkeypatch.setattr(api.channels, "resolve_channel_id", lambda x: mock_channel["channel_id"])
    monkeypatch.setattr(db, "get_topic", lambda x: mock_channel["topic"])

    return Council(mock_channel["channel_name"])


@pytest.fixture
def mock_registry_identity():
    """Mock identity registry."""

    def get_identity(agent_id):
        identities = {
            "agent-1": "alice",
            "agent-2": "bob",
        }
        return identities.get(agent_id, agent_id)

    return get_identity
