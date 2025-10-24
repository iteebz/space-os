import pytest

from space.os import config, db
from space.os.bridge import db as bridge_db
from space.os.bridge import migrations as bridge_migrations
from space.os.knowledge import db as knowledge_db
from space.os.knowledge import migrations as knowledge_migrations
from space.os.memory import db as memory_db
from space.os.memory import migrations as memory_migrations
from space.os.spawn import db as spawn_db
from space.os.spawn import migrations as spawn_migrations


@pytest.fixture(autouse=True)
def clear_config_cache():
    config.clear_cache()


@pytest.fixture
def test_space(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")
    (workspace / ".space").mkdir()

    from space.os.lib import paths

    monkeypatch.setattr(paths, "space_root", lambda base_path=None: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: workspace / ".space")

    from space.os.db import sqlite

    monkeypatch.setattr(sqlite, "paths", paths)

    from space.os import events

    events.DB_PATH = workspace / ".space" / "events.db"

    for path in [
        workspace / ".space",
        workspace / ".space" / "bridge",
        workspace / ".space" / "security",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    from space.os import config as cfg

    registry_db_path = workspace / ".space" / cfg.registry_db().name
    db.ensure_schema(
        registry_db_path,
        spawn_db.SCHEMA,
        spawn_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        workspace / ".space" / memory_db.MEMORY_DB_NAME,
        memory_db.SCHEMA,
        memory_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        workspace / ".space" / knowledge_db.KNOWLEDGE_DB_NAME,
        knowledge_db.SCHEMA,
        knowledge_migrations.MIGRATIONS,
    )

    db.ensure_schema(
        workspace / ".space" / "bridge.db",
        bridge_db.SCHEMA,
        bridge_migrations.MIGRATIONS,
    )

    spawn_db.clear_identity_cache()

    yield workspace
