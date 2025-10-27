import contextlib
import gc
import shutil
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from space.lib import paths, store
from space.os import bridge, knowledge, memory, spawn
from space.os.spawn import defaults as spawn_defaults


@pytest.fixture(scope="session")
def _seed_dbs(tmp_path_factory):
    seed_dir = tmp_path_factory.mktemp("seed_dbs")

    spawn.db.register()
    with spawn.db.connect():
        pass

    for db_module, _db_name in [
        (memory.db, "memory.db"),
        (knowledge.db, "knowledge.db"),
        (bridge.db, "bridge.db"),
    ]:
        store.ensure(db_module.__name__.split(".")[-2])

    return seed_dir


@pytest.fixture
def test_space(monkeypatch, tmp_path, _seed_dbs):
    store.close_all()
    spawn.api.agents._clear_cache()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    def paths_override(base_path=None):
        return workspace

    monkeypatch.setattr(paths, "space_root", paths_override)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")
    monkeypatch.setattr(paths, "space_data", lambda base_path=None: workspace / ".space")

    spawn.db._initialized = False
    memory.db._initialized = False
    knowledge.db._initialized = False
    bridge.db._initialized = False

    spawn.db.register()
    memory.db.register()
    knowledge.db.register()
    bridge.db.register()

    for subdir in ["", "bridge", "knowledge"]:
        (workspace / ".space" / subdir).mkdir(parents=True, exist_ok=True)

    for db_name in ["spawn.db", "memory.db", "knowledge.db", "bridge.db"]:
        src = _seed_dbs / db_name
        dst = workspace / ".space" / db_name
        if src.exists():
            shutil.copy2(src, dst)
            for suffix in ["-wal", "-shm"]:
                wal = src.parent / f"{src.name}{suffix}"
                if wal.exists():
                    shutil.copy2(wal, workspace / ".space" / wal.name)

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
