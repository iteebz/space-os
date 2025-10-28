import contextlib
import gc
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from space.lib import paths, store
from space.os import bridge, knowledge, memory, spawn
from space.os import db as unified_db
from space.os.spawn import defaults as spawn_defaults


def _configure_paths(monkeypatch: pytest.MonkeyPatch, workspace: Path) -> None:
    data_dir = workspace / ".space" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(paths, "space_root", lambda: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda: data_dir)


def _reset_runtime_state() -> None:
    store._reset_for_testing()
    spawn.api.agents._clear_cache()
    unified_db._initialized = False  # type: ignore[attr-defined]
    for module in (spawn.db, memory.db, knowledge.db, bridge.db):
        if hasattr(module, "_initialized"):
            setattr(module, "_initialized", False)


@pytest.fixture
def test_space(monkeypatch, tmp_path):
    _reset_runtime_state()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    _configure_paths(monkeypatch, workspace)
    unified_db.register()
    with unified_db.connect():
        pass

    yield workspace

    spawn.api.agents._clear_cache()
    store.close_all()
    gc.collect()
    for obj in gc.get_objects():
        if isinstance(obj, sqlite3.Connection):
            with contextlib.suppress(Exception):
                obj.close()


@pytest.fixture
def mock_db():
    """Mock db.ensure context manager for unit tests."""
    mock_conn = MagicMock()
    with patch("space.lib.store.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = mock_conn
        mock_ensure.return_value.__exit__.return_value = None
        yield mock_conn


@pytest.fixture
def mock_resolve_channel():
    """Standardize channel resolution patching for bridge-focused tests."""

    def _resolve(identifier):
        channel_id = getattr(identifier, "channel_id", identifier)
        if channel_id is None:
            channel_id = ""
        return MagicMock(channel_id=channel_id)

    with patch("space.os.bridge.api.channels.resolve_channel") as mock:
        mock.side_effect = _resolve
        yield mock


class AgentHandle(str):
    """String-like handle exposing agent metadata for tests."""

    def __new__(cls, identity: str, agent_id: str, model: str, constitution: str | None):
        obj = str.__new__(cls, identity)
        obj.agent_id = agent_id
        obj.model = model
        obj.constitution = constitution
        return obj


@pytest.fixture
def default_agents(test_space):
    """Registers a set of default agents for tests and returns their identities."""
    from space.os import spawn

    handles: dict[str, AgentHandle] = {}
    for identity in spawn_defaults.DEFAULT_AGENT_MODELS:
        with contextlib.suppress(ValueError):
            model = spawn_defaults.canonical_model(identity)
            spawn.register_agent(identity, model, f"{identity}.md")
        agent = spawn.get_agent(identity)
        assert agent is not None
        handles[identity] = AgentHandle(
            agent.identity, agent.agent_id, agent.model, agent.constitution
        )
    return handles
