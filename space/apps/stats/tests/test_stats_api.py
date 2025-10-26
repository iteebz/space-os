"""Stats aggregation API tests."""

from unittest.mock import patch

import pytest

from space.apps.stats import api
from space.apps.stats.models import BridgeStats, KnowledgeStats, MemoryStats, SpaceStats, SpawnStats


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


def test_bridge_stats_returns_bridge_stats_object(mock_apis):
    mock_apis["bridge"].api.stats.return_value = {
        "messages": {"total": 100, "active": 80, "archived": 20, "by_agent": []},
        "channels": {"total": 10, "active": 8, "archived": 2},
        "notes": 5,
        "events": {"total": 0, "by_agent": []},
    }
    mock_apis["spawn"].api.agent_identities.return_value = {}

    result = api.bridge_stats()

    assert isinstance(result, BridgeStats)
    assert result.available is True
    assert result.total == 100
    assert result.active == 80


def test_bridge_stats_handles_exception(mock_apis):
    mock_apis["bridge"].api.stats.side_effect = Exception("DB error")

    result = api.bridge_stats()

    assert isinstance(result, BridgeStats)
    assert result.available is False


def test_memory_stats_returns_memory_stats_object(mock_apis):
    mock_apis["memory"].api.stats.return_value = {
        "total": 50,
        "active": 45,
        "archived": 5,
        "topics": 10,
        "mem_by_agent": [],
    }
    mock_apis["spawn"].api.agent_identities.return_value = {}

    result = api.memory_stats()

    assert isinstance(result, MemoryStats)
    assert result.available is True
    assert result.total == 50


def test_memory_stats_handles_exception(mock_apis):
    mock_apis["memory"].api.stats.side_effect = Exception("DB error")

    result = api.memory_stats()

    assert isinstance(result, MemoryStats)
    assert result.available is False


def test_knowledge_stats_returns_knowledge_stats_object(mock_apis):
    mock_apis["knowledge"].api.stats.return_value = {
        "total": 30,
        "active": 25,
        "archived": 5,
        "topics": 8,
        "know_by_agent": [],
    }
    mock_apis["spawn"].api.agent_identities.return_value = {}

    result = api.knowledge_stats()

    assert isinstance(result, KnowledgeStats)
    assert result.available is True
    assert result.total == 30


def test_knowledge_stats_handles_exception(mock_apis):
    mock_apis["knowledge"].api.stats.side_effect = Exception("DB error")

    result = api.knowledge_stats()

    assert isinstance(result, KnowledgeStats)
    assert result.available is False


def test_spawn_stats_returns_spawn_stats_object(mock_apis):
    mock_apis["spawn"].api.stats.return_value = {
        "total": 5,
        "active": 4,
        "archived": 1,
        "hashes": 2,
    }

    result = api.spawn_stats()

    assert isinstance(result, SpawnStats)
    assert result.available is True
    assert result.total == 5


def test_spawn_stats_handles_exception(mock_apis):
    mock_apis["spawn"].api.stats.side_effect = Exception("DB error")

    result = api.spawn_stats()

    assert isinstance(result, SpawnStats)
    assert result.available is False


def test_collect_returns_space_stats(mock_apis):
    mock_apis["bridge"].api.stats.return_value = {
        "messages": {"total": 100, "active": 80, "archived": 20, "by_agent": []},
        "channels": {"total": 10, "active": 8, "archived": 2},
        "notes": 5,
        "events": {"total": 0, "by_agent": []},
    }
    mock_apis["memory"].api.stats.return_value = {
        "total": 50,
        "active": 45,
        "archived": 5,
        "topics": 10,
        "mem_by_agent": [],
    }
    mock_apis["knowledge"].api.stats.return_value = {
        "total": 30,
        "active": 25,
        "archived": 5,
        "topics": 8,
        "know_by_agent": [],
    }
    mock_apis["spawn"].api.stats.return_value = {
        "total": 5,
        "active": 4,
        "archived": 1,
        "hashes": 2,
    }
    mock_apis["spawn"].api.agent_identities.return_value = {}
    mock_apis["spawn"].api.archived_agents.return_value = set()

    result = api.collect()

    assert isinstance(result, SpaceStats)
    assert isinstance(result.bridge, BridgeStats)
    assert isinstance(result.memory, MemoryStats)
    assert isinstance(result.knowledge, KnowledgeStats)
    assert isinstance(result.spawn, SpawnStats)
