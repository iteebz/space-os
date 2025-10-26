"""Integration tests for chats primitive across all providers."""

import json

import pytest

from space.core import chats


@pytest.fixture
def mock_claude_chats(tmp_path):
    """Create mock Claude chat files."""
    project_dir = tmp_path / "claude" / "projects" / "test_project"
    project_dir.mkdir(parents=True)

    chat_file = project_dir / "session123.jsonl"
    messages = [
        {"type": "user", "message": "hello claude", "timestamp": "2025-01-01T10:00:00"},
        {"type": "assistant", "message": "hi there", "timestamp": "2025-01-01T10:00:01"},
        {"type": "user", "message": "how are you", "timestamp": "2025-01-01T10:00:02"},
    ]

    with open(chat_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return {"dir": project_dir.parent.parent, "file": chat_file, "cli": "claude"}


@pytest.fixture
def mock_codex_chats(tmp_path):
    """Create mock Codex chat files."""
    sessions_dir = tmp_path / "codex" / "sessions" / "subdir"
    sessions_dir.mkdir(parents=True)

    chat_file = sessions_dir / "session456.jsonl"
    messages = [
        {"type": "turn_context", "payload": {"model": "gpt-4"}},
        {
            "type": "response_item",
            "payload": {"role": "user", "content": "fix this bug"},
            "timestamp": "2025-01-01T11:00:00",
        },
        {
            "type": "response_item",
            "payload": {"role": "assistant", "content": "bug fixed"},
            "timestamp": "2025-01-01T11:00:01",
        },
    ]

    with open(chat_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return {"dir": sessions_dir.parent.parent, "file": chat_file, "cli": "codex"}


@pytest.fixture
def mock_gemini_chats(tmp_path):
    """Create mock Gemini chat files."""
    gemini_dir = tmp_path / "gemini" / "tmp" / "abc123def456"
    gemini_dir.mkdir(parents=True)

    chat_file = gemini_dir / "session-789.json"
    data = {
        "sessionId": "session789",
        "messages": [
            {"role": "user", "content": "hello gemini", "timestamp": "2025-01-01T12:00:00"},
            {"role": "model", "content": "hello user", "timestamp": "2025-01-01T12:00:01"},
        ],
    }

    with open(chat_file, "w") as f:
        json.dump(data, f)

    return {"dir": gemini_dir.parent.parent, "file": chat_file, "cli": "gemini"}


def test_claude_provider_discover(mock_claude_chats, monkeypatch):
    """Test Claude provider discovers sessions."""
    from space.lib.providers import Claude

    provider = Claude()

    sessions = provider.discover_sessions()
    assert isinstance(sessions, list)


def test_claude_provider_parse_messages(mock_claude_chats):
    """Test Claude provider parses messages."""
    from space.lib.providers import Claude

    provider = Claude()
    messages = provider.parse_messages(mock_claude_chats["file"])

    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert "hello claude" in messages[0]["content"]
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"


def test_codex_provider_discover(mock_codex_chats):
    """Test Codex provider discovers sessions."""
    from space.lib.providers import Codex

    provider = Codex()

    sessions = provider.discover_sessions()
    assert isinstance(sessions, list)


def test_codex_provider_parse_messages(mock_codex_chats):
    """Test Codex provider parses messages."""
    from space.lib.providers import Codex

    provider = Codex()
    messages = provider.parse_messages(mock_codex_chats["file"])

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_gemini_provider_discover(mock_gemini_chats):
    """Test Gemini provider discovers sessions."""
    from space.lib.providers import Gemini

    provider = Gemini()

    sessions = provider.discover_sessions()
    assert isinstance(sessions, list)


def test_gemini_provider_parse_messages(mock_gemini_chats):
    """Test Gemini provider parses messages."""
    from space.lib.providers import Gemini

    provider = Gemini()
    messages = provider.parse_messages(mock_gemini_chats["file"])

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_offset_tracking(test_space):
    """Test offset tracking stores sync state."""
    from space.lib import store

    with store.ensure("chats") as conn:
        conn.execute(
            "INSERT INTO sessions (cli, session_id, file_path) VALUES (?, ?, ?)",
            ("claude", "session123", "/tmp/test.jsonl"),
        )
        conn.execute(
            "INSERT INTO syncs (cli, session_id) VALUES (?, ?)",
            ("claude", "session123"),
        )

    chats.update_sync_state("claude", "session123", byte_offset=512)

    state = chats.get_sync_state("claude", "session123")
    assert state is not None
    assert state["last_byte_offset"] == 512


def test_identity_linking(test_space):
    """Test linking sessions to identities."""
    from space.lib import store

    with store.ensure("chats") as conn:
        conn.execute(
            "INSERT INTO sessions (cli, session_id, file_path) VALUES (?, ?, ?)",
            ("claude", "session123", "/tmp/test.jsonl"),
        )

    chats.link("session123", identity="hailot")

    sessions = chats.get_by_identity("hailot")
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session123"


def test_task_linking(test_space):
    """Test linking sessions to tasks."""
    from space.lib import store

    with store.ensure("chats") as conn:
        conn.execute(
            "INSERT INTO sessions (cli, session_id, file_path) VALUES (?, ?, ?)",
            ("claude", "session456", "/tmp/test.jsonl"),
        )

    chats.link("session456", task_id="task-abc123")

    sessions = chats.get_by_task_id("task-abc123")
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session456"
