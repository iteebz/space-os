import contextlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from space.core import db
from space.lib import paths, store
from space.os import bridge, spawn
from space.os.spawn import defaults as spawn_defaults


def _configure_paths(monkeypatch: pytest.MonkeyPatch, workspace: Path, test_name: str) -> None:
    data_dir = workspace / test_name / ".space" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "space.db"
    if db_path.exists():
        db_path.unlink()

    monkeypatch.setattr(paths, "space_root", lambda: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda: data_dir)


@pytest.fixture
def test_space(monkeypatch, tmp_path, request):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    data_dir = workspace / ".space" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_path = data_dir / "space.db"
    if db_path.exists():
        db_path.unlink()

    monkeypatch.setattr(paths, "space_root", lambda: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda: data_dir)

    store._reset_for_testing()
    db._initialized = False
    db.register()
    with db.connect():
        pass

    yield workspace


@pytest.fixture
def populated_space(test_space):
    # Create dummy constitution files for default agents
    for identity in spawn_defaults.DEFAULT_AGENT_MODELS:
        constitution_path = test_space / f"{identity}.md"
        constitution_path.write_text(
            f"# {identity} Constitution\n\nThis is a dummy constitution for {identity}."
        )

    # Register default channels for tests
    bridge.api.channels.resolve_channel("ch-1")
    bridge.api.channels.resolve_channel("ch-spawn-test-123")
    return test_space


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


def dump_agents_table():
    with db.connect() as conn:
        print("DEBUG: Contents of agents table:")
        for row in conn.execute("SELECT agent_id, identity FROM agents").fetchall():
            print(f"  agent_id: {row['agent_id']}, identity: {row['identity']}")


@pytest.fixture
def default_agents(test_space):
    """Registers a set of default agents for tests and returns their identities."""

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
