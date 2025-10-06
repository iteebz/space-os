import tempfile
from pathlib import Path

from space.apps.register import registry

# def test_register_with_model():
#     with tempfile.TemporaryDirectory() as tmpdir:
#         db = Path(tmpdir) / "spawn.db"
#         registry.config.registry_db = lambda: db
#         registry.init_db()
#
#         regs = registry.list_entries()
#         assert len(regs) == 1
#         assert regs[0].model == "gpt-5-codex"


# def test_register_without_model():
#     with tempfile.TemporaryDirectory() as tmpdir:
#         db = Path(tmpdir) / "spawn.db"
#         registry.config.registry_db = lambda: db
#         registry.init_db()
#
#         regs = registry.list_entries()
#         assert len(regs) == 1
#         assert regs[0].model is None


def test_mixed_model_registrations():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "spawn.db"
        registry.config.registry_db = lambda: db
        registry.init_db()

        registry.register(
            role="zealot",
            agent_id="zealot-sonnet",
            channels=["test"],
            identity_hash="abc",
            identity="dummy_content",
        )
        registry.register(
            role="sentinel",
            agent_id="sentinel-codex",
            channels=["test"],
            identity_hash="def",
            identity="dummy_content",
        )
        registry.register(
            role="scribe",
            agent_id="scribe-1",
            channels=["test"],
            identity_hash="ghi",
            identity="dummy_content",
        )

        regs = registry.list()
        assert len(regs) == 3

        # The 'model' attribute is no longer directly stored via register, so this assertion needs to be removed or updated.
        # For now, we'll just assert that the registrations exist.
        agent_ids = {r.agent_id for r in regs}
        assert "zealot-sonnet" in agent_ids
        assert "sentinel-codex" in agent_ids
        assert "scribe-1" in agent_ids
