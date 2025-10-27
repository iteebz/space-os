"""Unit tests for unified context search."""

from unittest.mock import patch

from space.apps.context.lib import api as context


def test_validate_search_term_valid():
    """Valid search terms pass validation."""
    context._validate_search_term("test")
    context._validate_search_term("a" * 256)


def test_validate_search_term_too_long():
    """Search term exceeding max length raises ValueError."""
    with patch.object(context, "_get_max_search_len", return_value=10):
        try:
            context._validate_search_term("a" * 11)
            raise AssertionError("Should raise ValueError")
        except ValueError as e:
            assert "Search term too long" in str(e)


def test_collect_timeline_deduplicates():
    """Timeline deduplicates by source and ID."""
    with (
        patch("space.apps.context.lib.api.memory.search") as m_mem,
        patch("space.apps.context.lib.api.knowledge.search") as m_know,
        patch("space.apps.context.lib.api.bridge.search") as m_bridge,
        patch("space.apps.context.lib.api._search_provider_chats") as m_chat,
        patch("space.apps.context.lib.api.canon.search") as m_canon,
    ):
        m_mem.return_value = [
            {
                "source": "memory",
                "memory_id": "id-1",
                "topic": "topic-a",
                "identity": "alice",
                "message": "thought 1",
                "timestamp": 100,
                "reference": "mem:1",
            }
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = context.collect_timeline("test", None, False)
        assert len(result) == 1
        assert result[0]["source"] == "memory"
        assert result[0]["type"] == "topic-a"


def test_collect_timeline_sorted_by_timestamp():
    """Timeline entries sorted by timestamp."""
    with (
        patch("space.apps.context.lib.api.memory.search") as m_mem,
        patch("space.apps.context.lib.api.knowledge.search") as m_know,
        patch("space.apps.context.lib.api.bridge.search") as m_bridge,
        patch("space.apps.context.lib.api._search_provider_chats") as m_chat,
        patch("space.apps.context.lib.api.canon.search") as m_canon,
    ):
        m_mem.return_value = [
            {
                "source": "memory",
                "memory_id": "id-2",
                "topic": "t1",
                "identity": "alice",
                "message": "msg2",
                "timestamp": 200,
                "reference": "r2",
            },
            {
                "source": "memory",
                "memory_id": "id-1",
                "topic": "t1",
                "identity": "alice",
                "message": "msg1",
                "timestamp": 100,
                "reference": "r1",
            },
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = context.collect_timeline("test", None, False)
        assert result[0]["timestamp"] < result[1]["timestamp"]


def test_collect_timeline_returns_last_10():
    """Timeline returns max 10 entries."""
    with (
        patch("space.apps.context.lib.api.memory.search") as m_mem,
        patch("space.apps.context.lib.api.knowledge.search") as m_know,
        patch("space.apps.context.lib.api.bridge.search") as m_bridge,
        patch("space.apps.context.lib.api._search_provider_chats") as m_chat,
        patch("space.apps.context.lib.api.canon.search") as m_canon,
    ):
        m_mem.return_value = [
            {
                "source": "memory",
                "memory_id": f"id-{i}",
                "topic": "t",
                "identity": "alice",
                "message": f"msg{i}",
                "timestamp": i,
                "reference": f"r{i}",
            }
            for i in range(15)
        ]
        m_know.return_value = []
        m_bridge.return_value = []
        m_chat.return_value = []
        m_canon.return_value = []

        result = context.collect_timeline("test", None, False)
        assert len(result) == 10
        assert result[-1]["timestamp"] == 14


def test_collect_current_state_all_sources():
    """Current state collects from all sources."""
    with (
        patch("space.apps.context.lib.api.memory.search") as m_mem,
        patch("space.apps.context.lib.api.knowledge.search") as m_know,
        patch("space.apps.context.lib.api.bridge.search") as m_bridge,
        patch("space.apps.context.lib.api._search_provider_chats") as m_chat,
        patch("space.apps.context.lib.api.canon.search") as m_canon,
    ):
        m_mem.return_value = [
            {"identity": "alice", "topic": "t1", "message": "m1", "reference": "r1"}
        ]
        m_know.return_value = [
            {"domain": "d1", "content": "c1", "contributor": "alice", "reference": "r1"}
        ]
        m_bridge.return_value = [
            {"channel_name": "ch1", "sender": "alice", "content": "c1", "reference": "r1"}
        ]
        m_chat.return_value = [
            {
                "cli": "cli1",
                "session_id": "s1",
                "identity": "alice",
                "role": "r1",
                "text": "t1",
                "reference": "r1",
            }
        ]
        m_canon.return_value = [{"path": "p1", "content": "c1", "reference": "r1"}]

        result = context.collect_current_state("test", None, False)
        assert "memory" in result
        assert "knowledge" in result
        assert "bridge" in result
        assert "provider_chats" in result
        assert "canon" in result
        assert len(result["memory"]) == 1
        assert len(result["knowledge"]) == 1
        assert len(result["bridge"]) == 1
        assert len(result["provider_chats"]) == 1
        assert len(result["canon"]) == 1
