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

        assert (
            result
            == "You are now sentinel.\n\nYou are a sentinel.\n\nInfrastructure: run `space` for commands and orientation (already in PATH)."
        )


def test_inject_identity_with_self():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        registry.set_self_description("sentinel-1", "Reality guardian")

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel-1")

        assert (
            result
            == "You are now sentinel-1.\nSelf: Reality guardian\n\nYou are a sentinel.\n\nInfrastructure: run `space` for commands and orientation (already in PATH)."
        )


def test_self_identity_evolution():
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


def test_inject_identity_with_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot-1", "claude-sonnet-4.5")

        assert (
            result
            == "You are now zealot-1 powered by claude-sonnet-4.5.\n\nYou are a zealot.\n\nInfrastructure: run `space` for commands and orientation (already in PATH)."
        )
