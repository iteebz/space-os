"""Pytest configuration for space-os tests."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db(monkeypatch):
    """Use temporary database for tests, ensuring true isolation."""
    from space import events
    from space.knowledge import db as knowledge_db
    from space.memory import db as memory_db
    from space.spawn import config as spawn_config

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_space_dir = Path(tmpdir)
        monkeypatch.chdir(temp_space_dir)

        # Monkeypatch workspace_root for all dbs
        monkeypatch.setattr(spawn_config, "workspace_root", lambda: temp_space_dir)

        # Setup memory_db
        with memory_db.connect():
            pass

        # Setup knowledge_db
        knowledge_db_path = temp_space_dir / ".space" / "knowledge.db"
        monkeypatch.setattr(knowledge_db, "database_path", lambda: knowledge_db_path)
        with knowledge_db.connect():
            pass

        # Setup events_db
        events_db_path = temp_space_dir / ".space" / "events.db"
        original_events_db_path = events.DB_PATH
        events.DB_PATH = events_db_path
        events._ensure_db()

        yield temp_space_dir

        # Teardown events_db
        events.DB_PATH = original_events_db_path


@pytest.fixture
def bridge_workspace(monkeypatch, tmp_path):
    """Provide isolated workspace for bridge tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    # Keep all home-directory lookups inside temporary sandbox.
    monkeypatch.setattr(Path, "home", lambda: workspace)

    from space.bridge import config as bridge_config
    from space.spawn import config as spawn_config

    monkeypatch.setattr(spawn_config, "workspace_root", lambda: workspace)

    # Repoint bridge configuration to the temporary workspace.
    bridge_config.SPACE_DIR = workspace / ".space"
    bridge_config.BRIDGE_DIR = bridge_config.SPACE_DIR / "bridge"
    bridge_config.IDENTITIES_DIR = bridge_config.BRIDGE_DIR / "identities"
    bridge_config.DB_PATH = bridge_config.SPACE_DIR / "bridge.db"
    bridge_config.CONFIG_FILE = bridge_config.SPACE_DIR / "config.json"
    bridge_config.SENTINEL_LOG_PATH = bridge_config.SPACE_DIR / "security" / "sentinel.log"
    bridge_config.LEGACY_BRIDGE_DIR = workspace / ".legacy_bridge"
    bridge_config.LEGACY_SPACE_DIR = workspace / ".legacy_space"
    bridge_config._config = {}

    for path in [
        bridge_config.SPACE_DIR,
        bridge_config.BRIDGE_DIR,
        bridge_config.IDENTITIES_DIR,
        bridge_config.SENTINEL_LOG_PATH.parent,
        bridge_config.LEGACY_BRIDGE_DIR,
        bridge_config.LEGACY_SPACE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    yield workspace


@pytest.fixture
def spawn_workspace(monkeypatch, tmp_path):
    """Provide isolated workspace for spawn tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    from space.spawn import config as spawn_config
    from space.spawn import registry

    monkeypatch.setattr(spawn_config, "workspace_root", lambda: workspace)

    space_dir = workspace / ".space"
    space_dir.mkdir(parents=True, exist_ok=True)

    registry.init_db()

    yield workspace
