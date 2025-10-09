import sqlite3
import tempfile
from pathlib import Path

from space.spawn import registry, spawn


def test_inject_identity_no_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel")

        assert result == "You are now sentinel.\nYou are a sentinel."


def test_inject_identity_with_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO registrations (role, sender_id, topic, constitution_hash, self) VALUES (?, ?, ?, ?, ?)",
            ("sentinel", "sentinel-1", "detective", "abc123", "Reality guardian"),
        )
        conn.commit()
        conn.close()

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel-1")

        assert result == "You are now sentinel-1.\nSelf: Reality guardian\n\nYou are a sentinel."


def test_self_identity_evolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO registrations (role, sender_id, topic, constitution_hash) VALUES (?, ?, ?, ?)",
            ("zealot", "zealot-1", "space", "def456"),
        )
        conn.commit()

        conn.execute(
            "UPDATE registrations SET self = ? WHERE sender_id = ?", ("Purges bullshit", "zealot-1")
        )
        conn.commit()

        row = conn.execute(
            "SELECT self FROM registrations WHERE sender_id = ?", ("zealot-1",)
        ).fetchone()
        conn.close()

        assert row[0] == "Purges bullshit"

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot-1")
        assert "Purges bullshit" in result


def test_describe_updates_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO registrations (role, sender_id, topic, constitution_hash) VALUES (?, ?, ?, ?)",
            ("scribe", "scribe-1", "council", "ghi789"),
        )
        conn.commit()

        cursor = conn.execute(
            "UPDATE registrations SET self = ? WHERE sender_id = ?",
            ("Voice of the council", "scribe-1"),
        )
        conn.commit()

        desc = conn.execute(
            "SELECT self FROM registrations WHERE sender_id = ?", ("scribe-1",)
        ).fetchone()[0]
        conn.close()

        assert cursor.rowcount > 0
        assert desc == "Voice of the council"


def test_inject_identity_with_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot-1", "claude-sonnet-4.5")

        assert result == "You are now zealot-1 powered by claude-sonnet-4.5.\nYou are a zealot."
