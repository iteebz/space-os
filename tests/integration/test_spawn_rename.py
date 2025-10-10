import sqlite3
from pathlib import Path

from space.spawn import registry


def test_rename(tmp_path: Path, monkeypatch):
    db = tmp_path / "spawn.db"
    monkeypatch.setattr(registry.config, "registry_db", lambda: db)
    registry.init_db()

    registry.set_self_description("crucible-1", "TDD purist")

    assert registry.rename_agent("crucible-1", "crucible")

    desc = registry.get_self_description("crucible")
    assert desc == "TDD purist"

    old_desc = registry.get_self_description("crucible-1")
    assert old_desc is None


def test_rename_nonexistent(tmp_path: Path, monkeypatch):
    db = tmp_path / "spawn.db"
    monkeypatch.setattr(registry.config, "registry_db", lambda: db)
    registry.init_db()

    assert not registry.rename_agent("nonexistent", "newname")


def test_agents_table_has_uuid(tmp_path: Path, monkeypatch):
    db = tmp_path / "spawn.db"
    monkeypatch.setattr(registry.config, "registry_db", lambda: db)
    registry.init_db()

    registry.set_self_description("test-agent", "Test description")

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT id, name FROM agents WHERE name = ?", ("test-agent",)).fetchone()
    conn.close()

    assert row is not None
    assert len(row["id"]) == 36
    assert row["name"] == "test-agent"
