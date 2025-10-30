"""Tests for stats aggregation functionality."""

from unittest.mock import patch

import pytest

from space.apps.stats import api
from space.apps.stats.models import LeaderboardEntry


@pytest.fixture
def mock_get_agent_identities():
    """Mock _get_agent_identities."""
    with patch("space.apps.stats.api._get_agent_identities") as mock:
        yield mock


@pytest.fixture
def mock_get_archived_agents():
    """Mock _get_archived_agents."""
    with patch("space.apps.stats.api._get_archived_agents") as mock:
        yield mock


@pytest.fixture
def mock_get_bridge_stats():
    """Mock _get_bridge_stats."""
    with patch("space.apps.stats.api._get_bridge_stats") as mock:
        yield mock


@pytest.fixture
def mock_get_memory_stats():
    """Mock _get_memory_stats."""
    with patch("space.apps.stats.api._get_memory_stats") as mock:
        yield mock


@pytest.fixture
def mock_get_knowledge_stats():
    """Mock _get_knowledge_stats."""
    with patch("space.apps.stats.api._get_knowledge_stats") as mock:
        yield mock


def test_build_leaderboard_empty(mock_get_agent_identities):
    mock_get_agent_identities.return_value = {}

    result = api._build_leaderboard([])

    assert result == []


def test_build_leaderboard_with_agents(mock_get_agent_identities):
    mock_get_agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }

    result = api._build_leaderboard(
        [
            {"agent_id": "agent1", "count": 10},
            {"agent_id": "agent2", "count": 5},
        ]
    )

    assert len(result) == 2
    assert result[0] == LeaderboardEntry(identity="Alice", count=10)
    assert result[1] == LeaderboardEntry(identity="Bob", count=5)


def test_build_leaderboard_with_limit(mock_get_agent_identities):
    mock_get_agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
        "agent3": "Charlie",
    }

    result = api._build_leaderboard(
        [
            {"agent_id": "agent1", "count": 10},
            {"agent_id": "agent2", "count": 5},
            {"agent_id": "agent3", "count": 3},
        ],
        limit=2,
    )

    assert len(result) == 2
    assert result[0].identity == "Alice"
    assert result[1].identity == "Bob"


def test_build_leaderboard_unknown_agent(mock_get_agent_identities):
    mock_get_agent_identities.return_value = {"agent1": "Alice"}

    result = api._build_leaderboard(
        [
            {"agent_id": "agent1", "count": 10},
            {"agent_id": "unknown", "count": 5},
        ]
    )

    assert len(result) == 2
    assert result[0].identity == "Alice"
    assert result[1].identity == "unknown"


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

    result = api.agent_stats()

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

    result = api.agent_stats()

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

    result = api.agent_stats(show_all=True)

    assert len(result) == 2
