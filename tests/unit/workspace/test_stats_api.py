"""Tests for stats aggregation functionality."""

from unittest.mock import patch

import pytest

from space.workspace import stats as stats_api


@pytest.fixture
def mock_get_agent_identities():
    """Mock _get_agent_identities."""
    with patch("space.workspace.stats._get_agent_identities") as mock:
        yield mock


@pytest.fixture
def mock_get_archived_agents():
    """Mock _get_archived_agents."""
    with patch("space.workspace.stats._get_archived_agents") as mock:
        yield mock


@pytest.fixture
def mock_get_bridge_stats():
    """Mock _get_bridge_stats."""
    with patch("space.workspace.stats._get_bridge_stats") as mock:
        yield mock


@pytest.fixture
def mock_get_memory_stats():
    """Mock _get_memory_stats."""
    with patch("space.workspace.stats._get_memory_stats") as mock:
        yield mock


@pytest.fixture
def mock_get_knowledge_stats():
    """Mock _get_knowledge_stats."""
    with patch("space.workspace.stats._get_knowledge_stats") as mock:
        yield mock


def test_agent_stats_aggregates_data(
    mock_get_agent_identities,
    mock_get_archived_agents,
    mock_get_bridge_stats,
    mock_get_memory_stats,
    mock_get_knowledge_stats,
):
    mock_get_agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }
    mock_get_archived_agents.return_value = set()

    mock_get_bridge_stats.return_value = {
        "messages": {"by_agent": [{"agent_id": "agent1", "count": 10}]},
        "events": {
            "by_agent": [
                {"agent_id": "agent1", "events": 5, "spawns": 1, "last_active": "2024-01-01"}
            ]
        },
    }
    mock_get_memory_stats.return_value = {"mem_by_agent": [{"agent_id": "agent1", "count": 3}]}
    mock_get_knowledge_stats.return_value = {"know_by_agent": [{"agent_id": "agent1", "count": 2}]}

    result = stats_api.agent_stats()

    assert len(result) == 2
    alice = next(a for a in result if a.agent_id == "agent1")
    assert alice.identity == "Alice"
    assert alice.msgs == 10
    assert alice.mems == 3
    assert alice.knowledge == 2
    assert alice.events == 5
    assert alice.spawns == 1


def test_agent_stats_filters_archived(
    mock_get_agent_identities,
    mock_get_archived_agents,
    mock_get_bridge_stats,
    mock_get_memory_stats,
    mock_get_knowledge_stats,
):
    mock_get_agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }
    mock_get_archived_agents.return_value = {"agent2"}

    mock_get_bridge_stats.return_value = {
        "messages": {"by_agent": []},
        "events": {"by_agent": []},
    }
    mock_get_memory_stats.return_value = {"mem_by_agent": []}
    mock_get_knowledge_stats.return_value = {"know_by_agent": []}

    result = stats_api.agent_stats()

    assert len(result) == 1
    assert result[0].agent_id == "agent1"


def test_agent_stats_show_all(
    mock_get_agent_identities,
    mock_get_archived_agents,
    mock_get_bridge_stats,
    mock_get_memory_stats,
    mock_get_knowledge_stats,
):
    mock_get_agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }
    mock_get_archived_agents.return_value = {"agent2"}

    mock_get_bridge_stats.return_value = {
        "messages": {"by_agent": []},
        "events": {"by_agent": []},
    }
    mock_get_memory_stats.return_value = {"mem_by_agent": []}
    mock_get_knowledge_stats.return_value = {"know_by_agent": []}

    result = stats_api.agent_stats(show_all=True)

    assert len(result) == 2
