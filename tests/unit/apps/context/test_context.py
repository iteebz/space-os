"""Unit tests for unified context search."""

from unittest.mock import patch

from space.apps.context.api import (
    _validate_search_term,
    collect_current_state,
    collect_timeline,
)
from space.core.models import SearchResult


def test_validate_search_term_valid():
    """Valid search terms pass validation."""
    _validate_search_term("test")
    _validate_search_term("a" * 256)


def test_validate_search_term_too_long():
    """Search term exceeding max length raises ValueError."""
    try:
        _validate_search_term("a" * 257)
        raise AssertionError("Should raise ValueError")
    except ValueError as e:
        assert "Search term too long" in str(e)


def test_collect_timeline_memory_excluded_without_identity():
    """Timeline excludes memory when no --as identity provided."""
    with (
        patch("space.apps.context.api.memory.api.search") as m_mem,
        patch("space.apps.context.api.knowledge.api.search") as m_know,
        patch("space.apps.context.api.bridge.api.search") as m_bridge,
        patch("space.apps.context.api.sessions.api.search") as m_chat,
        patch("space.os.canon.api.search") as m_canon,
    ):
        m_mem.return_value = [
            {
                "source": "memory",
                "memory_id": "id-1",
                "topic": "topic-a",
                "message": "thought 1",
                "timestamp": 100,
                "reference": "mem:1",
            }
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = collect_timeline("test", None, False)
        assert len(result) == 0
        m_mem.assert_not_called()


def test_collect_timeline_memory_included_with_identity():
    """Timeline includes memory when --as identity is specified."""
    with (
        patch("space.apps.context.api.memory.api.search") as m_mem,
        patch("space.apps.context.api.knowledge.api.search") as m_know,
        patch("space.apps.context.api.bridge.api.search") as m_bridge,
        patch("space.apps.context.api.sessions.api.search") as m_chat,
        patch("space.os.canon.api.search") as m_canon,
    ):
        m_mem.return_value = [
            SearchResult(
                source="memory",
                reference="mem:1",
                content="thought 1",
                timestamp="2025-01-01T00:01:40",
                agent_id="agent-1",
                identity="alice",
                metadata={"memory_id": "id-1", "topic": "topic-a"},
            )
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = collect_timeline("test", "alice", False)
        assert len(result) == 1
        assert result[0]["source"] == "memory"
        assert result[0]["type"] == "topic-a"
        m_mem.assert_called_once()


def test_collect_timeline_sorted_by_timestamp():
    """Timeline entries sorted by timestamp."""
    with (
        patch("space.apps.context.api.memory.api.search") as m_mem,
        patch("space.apps.context.api.knowledge.api.search") as m_know,
        patch("space.apps.context.api.bridge.api.search") as m_bridge,
        patch("space.apps.context.api.sessions.api.search") as m_chat,
        patch("space.os.canon.api.search") as m_canon,
    ):
        m_mem.return_value = [
            SearchResult(
                source="memory",
                reference="r2",
                content="msg2",
                timestamp="2025-01-01T00:03:20",
                agent_id="a1",
                identity="alice",
                metadata={"memory_id": "id-2", "topic": "t1"},
            ),
            SearchResult(
                source="memory",
                reference="r1",
                content="msg1",
                timestamp="2025-01-01T00:01:40",
                agent_id="a1",
                identity="alice",
                metadata={"memory_id": "id-1", "topic": "t1"},
            ),
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = collect_timeline("test", "alice", False)
        assert result[0]["timestamp"] < result[1]["timestamp"]


def test_collect_timeline_returns_last_10():
    """Timeline returns max 10 entries."""
    with (
        patch("space.apps.context.api.memory.api.search") as m_mem,
        patch("space.apps.context.api.knowledge.api.search") as m_know,
        patch("space.apps.context.api.bridge.api.search") as m_bridge,
        patch("space.apps.context.api.sessions.api.search") as m_chat,
        patch("space.os.canon.api.search") as m_canon,
    ):
        m_mem.return_value = [
            SearchResult(
                source="memory",
                reference=f"r{i}",
                content=f"msg{i}",
                timestamp=f"2025-01-01T00:00:{i:02d}",
                agent_id="a1",
                identity="alice",
                metadata={"memory_id": f"id-{i}", "topic": "t"},
            )
            for i in range(15)
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = collect_timeline("test", "alice", False)
        assert len(result) == 10


def test_collect_current_state_memory_excluded_without_identity():
    """Current state excludes memory when no --as identity provided."""
    with (
        patch("space.apps.context.api.memory.api.search") as m_mem,
        patch("space.apps.context.api.knowledge.api.search") as m_know,
        patch("space.apps.context.api.bridge.api.search") as m_bridge,
        patch("space.apps.context.api.sessions.api.search") as m_chat,
        patch("space.os.canon.api.search") as m_canon,
    ):
        m_mem.return_value = [
            SearchResult(
                source="memory",
                reference="r1",
                content="m1",
                timestamp="2025-01-01T00:00:00",
                agent_id="a1",
                identity="alice",
                metadata={"topic": "t1"},
            )
        ]
        m_know.return_value = [
            SearchResult(
                source="knowledge",
                reference="r1",
                content="c1",
                timestamp="2025-01-01T00:00:00",
                agent_id="a1",
                identity="alice",
                metadata={"domain": "d1"},
            )
        ]
        m_bridge.return_value = [
            SearchResult(
                source="bridge",
                reference="r1",
                content="c1",
                timestamp="2025-01-01T00:00:00",
                agent_id="a1",
                identity="alice",
                metadata={"channel_name": "ch1"},
            )
        ]
        m_chat.return_value = [
            {
                "cli": "cli1",
                "session_id": "s1",
                "role": "r1",
                "text": "t1",
                "reference": "r1",
            }
        ]
        m_canon.return_value = [{"path": "p1", "content": "c1", "reference": "r1"}]

        result = collect_current_state("test", None, False)
        assert len(result["memory"]) == 0
        assert len(result["knowledge"]) == 1
        assert len(result["bridge"]) == 1
        assert len(result["sessions"]) == 1
        assert len(result["canon"]) == 1
        m_mem.assert_not_called()


def test_collect_current_state_memory_included_with_identity():
    """Current state includes memory when --as identity is specified."""
    with (
        patch("space.apps.context.api.memory.api.search") as m_mem,
        patch("space.apps.context.api.knowledge.api.search") as m_know,
        patch("space.apps.context.api.bridge.api.search") as m_bridge,
        patch("space.apps.context.api.sessions.api.search") as m_chat,
        patch("space.os.canon.api.search") as m_canon,
    ):
        m_mem.return_value = [
            SearchResult(
                source="memory",
                reference="r1",
                content="m1",
                timestamp="2025-01-01T00:00:00",
                agent_id="a1",
                identity="alice",
                metadata={"topic": "t1"},
            )
        ]
        m_know.return_value = [
            SearchResult(
                source="knowledge",
                reference="r1",
                content="c1",
                timestamp="2025-01-01T00:00:00",
                agent_id="a1",
                identity="alice",
                metadata={"domain": "d1"},
            )
        ]
        m_bridge.return_value = [
            SearchResult(
                source="bridge",
                reference="r1",
                content="c1",
                timestamp="2025-01-01T00:00:00",
                agent_id="a1",
                identity="alice",
                metadata={"channel_name": "ch1"},
            )
        ]
        m_chat.return_value = [
            {
                "cli": "cli1",
                "session_id": "s1",
                "role": "r1",
                "text": "t1",
                "reference": "r1",
            }
        ]
        m_canon.return_value = [{"path": "p1", "content": "c1", "reference": "r1"}]

        result = collect_current_state("test", "alice", False)
        assert len(result["memory"]) == 1
        assert len(result["knowledge"]) == 1
        assert len(result["bridge"]) == 1
        assert len(result["sessions"]) == 1
        assert len(result["canon"]) == 1
        m_mem.assert_called_once()
