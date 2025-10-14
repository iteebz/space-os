import tempfile
from pathlib import Path

from space.lib import paths
from space.spawn import registry, spawn


def test_inject_no_self(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        mocker.patch("space.lib.paths.space_root", return_value=Path(tmpdir))
        canon_path = paths.canon_path()
        canon_path.write_text("# CANON")
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel", "sentinel")

        assert "# SENTINEL CONSTITUTION" in result
        assert "Self: You are sentinel." in result
        assert "You are a sentinel." in result
        assert "# CANON" in result


def test_inject_with_self(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        mocker.patch("space.lib.paths.space_root", return_value=Path(tmpdir))
        canon_path = paths.canon_path()
        canon_path.write_text("# CANON")
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        registry.set_self_description("sentinel-1", "Reality guardian")

        const = "You are a sentinel."
        result = spawn.inject_identity(const, "sentinel", "sentinel-1")

        assert "# SENTINEL CONSTITUTION" in result
        assert "Self: You are sentinel-1." in result
        assert "You are a sentinel." in result
        assert "# CANON" in result


def test_evolution(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        mocker.patch("space.lib.paths.space_root", return_value=Path(tmpdir))
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        registry.set_self_description("zealot-1", "Purges bullshit")

        desc = registry.get_self_description("zealot-1")
        assert desc == "Purges bullshit"

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot", "zealot-1")
        assert "# ZEALOT CONSTITUTION" in result
        assert "Self: You are zealot-1." in result
        assert "You are a zealot." in result


def test_describe_updates_self(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        mocker.patch("space.lib.paths.space_root", return_value=Path(tmpdir))
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        updated = registry.set_self_description("scribe-1", "Voice of the council")
        desc = registry.get_self_description("scribe-1")

        assert updated
        assert desc == "Voice of the council"


def test_inject_with_model(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        mocker.patch("space.lib.paths.space_root", return_value=Path(tmpdir))
        canon_path = paths.canon_path()
        canon_path.write_text("# CANON")
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        const = "You are a zealot."
        result = spawn.inject_identity(const, "zealot", "zealot-1", "claude-sonnet-4.5")

        assert "# ZEALOT CONSTITUTION" in result
        assert "Self: You are zealot-1. Your model is claude-sonnet-4.5." in result
        assert "You are a zealot." in result
        assert "# CANON" in result
