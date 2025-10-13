import tempfile
from pathlib import Path

from space.spawn import registry, spawn


def test_inject_no_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel")

        assert "You are now sentinel." in result
        assert "You are a sentinel." in result
        assert "# CANON" in result
        assert (
            "Infrastructure: run `space` for commands and orientation (already in PATH)." in result
        )


def test_inject_with_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        registry.set_self_description("sentinel-1", "Reality guardian")

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel-1")

        assert "You are now sentinel-1." in result
        assert "Self: Reality guardian" in result
        assert "You are a sentinel." in result
        assert "# CANON" in result
        assert (
            "Infrastructure: run `space` for commands and orientation (already in PATH)." in result
        )


def test_evolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        registry.set_self_description("zealot-1", "Purges bullshit")

        desc = registry.get_self_description("zealot-1")
        assert desc == "Purges bullshit"

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot-1")
        assert "Purges bullshit" in result


def test_describe_updates_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        updated = registry.set_self_description("scribe-1", "Voice of the council")
        desc = registry.get_self_description("scribe-1")

        assert updated
        assert desc == "Voice of the council"


def test_inject_with_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot-1", "claude-sonnet-4.5")

        assert "You are now zealot-1 powered by claude-sonnet-4.5." in result
        assert "You are a zealot." in result
        assert "# CANON" in result
        assert (
            "Infrastructure: run `space` for commands and orientation (already in PATH)." in result
        )
