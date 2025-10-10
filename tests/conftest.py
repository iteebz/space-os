import contextlib
import sqlite3
from pathlib import Path

import pytest

from space.spawn import registry


@pytest.fixture
def test_space(monkeypatch, tmp_path):
    """Creates an isolated workspace for tests, with bridge and spawn initialized."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")
    (workspace / ".space").mkdir()

    from space.lib import paths

    monkeypatch.setattr(paths, "workspace_root", lambda: workspace)
    monkeypatch.setattr(Path, "home", lambda: workspace)

    from space import events
    from space.bridge import config as bridge_config
    
    events.DB_PATH = workspace / ".space" / "events.db"

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

    registry.init_db()

    yield workspace


@pytest.fixture
def in_memory_db():
    # Create a single in-memory connection
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Temporarily override registry.get_db to return this connection
    original_get_db = registry.get_db

    @contextlib.contextmanager
    def mock_get_db():
        yield conn

    registry.get_db = mock_get_db

    # Initialize schema for both tables on this connection
    registry.init_db()

    yield conn

    conn.close()
    registry.get_db = original_get_db  # Restore original
