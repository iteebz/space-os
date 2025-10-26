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


def test_gemini_provider_discover(mock_gemini_chats, monkeypatch):
    """Test Gemini provider discovers sessions."""
    from space.lib.providers import Gemini

    provider = Gemini()
    monkeypatch.setattr(provider, "tmp_dir", mock_gemini_chats["dir"] / "gemini" / "tmp")

    sessions = provider.discover_sessions()
    assert isinstance(sessions, list)


def test_gemini_provider_parse_messages(mock_gemini_chats):
    """Test Gemini provider parses messages from JSON."""
    from space.lib.providers import Gemini

    provider = Gemini()
    messages = provider.parse_messages(mock_gemini_chats["file"])

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_vault_copy_claude(mock_claude_chats, tmp_path, monkeypatch):
    """Test copying Claude JSONL to vault as-is."""
    from space.core.chats.api import vault
    from space.lib import paths

    monkeypatch.setattr(paths, "chats_dir", lambda: tmp_path / "vaults")

    vault_path = vault.copy_session_to_vault("claude", "session123", str(mock_claude_chats["file"]))

    assert (tmp_path / "vaults" / "claude" / "session123.jsonl").exists()
    assert vault_path == str(tmp_path / "vaults" / "claude" / "session123.jsonl")


def test_vault_copy_gemini_json_to_jsonl(mock_gemini_chats, tmp_path, monkeypatch):
    """Test converting Gemini JSON to JSONL in vault."""
    from space.core.chats.api import vault
    from space.lib import paths
    import json as stdlib_json

    monkeypatch.setattr(paths, "chats_dir", lambda: tmp_path / "vaults")

    vault_path = vault.copy_session_to_vault("gemini", "session789", str(mock_gemini_chats["file"]))

    assert (tmp_path / "vaults" / "gemini" / "session789.jsonl").exists()

    vault_file = tmp_path / "vaults" / "gemini" / "session789.jsonl"
    with open(vault_file) as f:
        lines = f.readlines()
    
    assert len(lines) == 2
    msg1 = stdlib_json.loads(lines[0])
    msg2 = stdlib_json.loads(lines[1])
    
    assert msg1["role"] == "user"
    assert msg2["role"] == "assistant"
    assert msg1["_provider"] == "gemini"


def test_search_in_vault_jsonl(test_space, tmp_path, monkeypatch):
    """Test searching raw JSONL files in vault."""
    from space.core.chats.api import search
    from space.lib import paths, store
    import json as stdlib_json

    vault_dir = tmp_path / "vault"
    monkeypatch.setattr(paths, "chats_dir", lambda: vault_dir)

    chat_file = vault_dir / "claude" / "session123.jsonl"
    chat_file.parent.mkdir(parents=True)

    with open(chat_file, "w") as f:
        f.write(stdlib_json.dumps({"role": "user", "content": "test query"}) + "\n")
        f.write(stdlib_json.dumps({"role": "assistant", "content": "answer"}) + "\n")

    with store.ensure("chats") as conn:
        conn.execute(
            "INSERT INTO sessions (cli, session_id, file_path) VALUES (?, ?, ?)",
            ("claude", "session123", str(chat_file)),
        )

    results = search.search("test query")
    assert len(results) == 1
    assert results[0]["content"] == "test query"
    assert results[0]["role"] == "user"


def test_export_session(test_space, tmp_path, monkeypatch):
    """Test exporting session messages with tool filtering."""
    from space.core.chats.api import export
    from space.lib import paths, store
    import json as stdlib_json

    vault_dir = tmp_path / "vault"
    monkeypatch.setattr(paths, "chats_dir", lambda: vault_dir)

    chat_file = vault_dir / "claude" / "session123.jsonl"
    chat_file.parent.mkdir(parents=True)

    with open(chat_file, "w") as f:
        f.write(stdlib_json.dumps({"role": "user", "content": "help"}) + "\n")
        f.write(stdlib_json.dumps({"role": "assistant", "content": "ok"}) + "\n")
        f.write(stdlib_json.dumps({"role": "tool", "content": "tool result"}) + "\n")

    with store.ensure("chats") as conn:
        conn.execute(
            "INSERT INTO sessions (cli, session_id, file_path) VALUES (?, ?, ?)",
            ("claude", "session123", str(chat_file)),
        )

    msgs = export.export("session123", "claude", include_tools=False)
    assert len(msgs) == 2
    assert all(m["role"] != "tool" for m in msgs)

    msgs_with_tools = export.export("session123", "claude", include_tools=True)
    assert len(msgs_with_tools) == 3


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
