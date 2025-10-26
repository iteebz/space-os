"""Tests for stats aggregation functionality."""

from unittest.mock import patch

import pytest

from space.apps.stats import api
from space.apps.stats.models import LeaderboardEntry


@pytest.fixture
def mock_apis():
    """Mock all core APIs."""
    with (
        patch("space.apps.stats.api.bridge") as mock_bridge,
        patch("space.apps.stats.api.memory") as mock_memory,
        patch("space.apps.stats.api.knowledge") as mock_knowledge,
        patch("space.apps.stats.api.spawn") as mock_spawn,
    ):
        yield {
            "bridge": mock_bridge,
            "memory": mock_memory,
            "knowledge": mock_knowledge,
            "spawn": mock_spawn,
        }


def test_build_leaderboard_empty(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {}

    result = api._build_leaderboard([])

    assert result == []


def test_build_leaderboard_with_agents(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {
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


def test_build_leaderboard_with_limit(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {
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


def test_build_leaderboard_unknown_agent(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {"agent1": "Alice"}

    result = api._build_leaderboard(
        [
            {"agent_id": "agent1", "count": 10},
            {"agent_id": "unknown", "count": 5},
        ]
    )

    assert len(result) == 2
    assert result[0].identity == "Alice"
    assert result[1].identity == "unknown"


def test_agent_stats_aggregates_data(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }
    mock_apis["spawn"].api.archived_agents.return_value = set()

    mock_apis["bridge"].api.stats.return_value = {
        "messages": {"by_agent": [{"agent_id": "agent1", "count": 10}]},
        "events": {
            "by_agent": [
                {"agent_id": "agent1", "events": 5, "spawns": 1, "last_active": "2024-01-01"}
            ]
        },
    }
    mock_apis["memory"].api.stats.return_value = {
        "mem_by_agent": [{"agent_id": "agent1", "count": 3}]
    }
    mock_apis["knowledge"].api.stats.return_value = {
        "know_by_agent": [{"agent_id": "agent1", "count": 2}]
    }

    result = api.agent_stats()

    assert len(result) == 2
    alice = next(a for a in result if a.agent_id == "agent1")
    assert alice.identity == "Alice"
    assert alice.msgs == 10
    assert alice.mems == 3
    assert alice.knowledge == 2
    assert alice.events == 5
    assert alice.spawns == 1


def test_agent_stats_filters_archived(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }
    mock_apis["spawn"].api.archived_agents.return_value = {"agent2"}

    mock_apis["bridge"].api.stats.return_value = {
        "messages": {"by_agent": []},
        "events": {"by_agent": []},
    }
    mock_apis["memory"].api.stats.return_value = {"mem_by_agent": []}
    mock_apis["knowledge"].api.stats.return_value = {"know_by_agent": []}

    result = api.agent_stats()

    assert len(result) == 1
    assert result[0].agent_id == "agent1"


def test_agent_stats_show_all(mock_apis):
    mock_apis["spawn"].api.agent_identities.return_value = {
        "agent1": "Alice",
        "agent2": "Bob",
    }
    mock_apis["spawn"].api.archived_agents.return_value = {"agent2"}

    mock_apis["bridge"].api.stats.return_value = {
        "messages": {"by_agent": []},
        "events": {"by_agent": []},
    }
    mock_apis["memory"].api.stats.return_value = {"mem_by_agent": []}
    mock_apis["knowledge"].api.stats.return_value = {"know_by_agent": []}

    result = api.agent_stats(show_all=True)

    assert len(result) == 2
