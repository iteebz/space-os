import tempfile
from pathlib import Path

from agent_space.spawn import registry, spawner


def test_register_with_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()
        
        reg_id = registry.register("zealot", "zealot-codex", "test", "abc123", "gpt-5-codex")
        
        regs = registry.list_registrations()
        assert len(regs) == 1
        assert regs[0].model == "gpt-5-codex"


def test_register_without_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()
        
        reg_id = registry.register("sentinel", "sentinel-1", "test", "def456")
        
        regs = registry.list_registrations()
        assert len(regs) == 1
        assert regs[0].model is None


def test_mixed_model_registrations():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()
        
        registry.register("zealot", "zealot-sonnet", "test", "abc", "claude-4.5-sonnet")
        registry.register("sentinel", "sentinel-codex", "test", "def", "gpt-5-codex")
        registry.register("scribe", "scribe-1", "test", "ghi")
        
        regs = registry.list_registrations()
        assert len(regs) == 3
        
        models = {r.sender_id: r.model for r in regs}
        assert models["zealot-sonnet"] == "claude-4.5-sonnet"
        assert models["sentinel-codex"] == "gpt-5-codex"
        assert models["scribe-1"] is None
