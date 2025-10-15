from space.lib import paths
from space.spawn import registry, spawn


def test_header_injection(tmp_path):
    """Verifies that the header is correctly injected."""
    db = tmp_path / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    constitution = "Core rules."
    result = spawn.inject_identity(constitution, "test-role", "test-agent", model="test-model")

    expected_header = "# TEST-ROLE CONSTITUTION"
    expected_self_desc = "Self: You are test-agent. Your model is test-model."

    assert result.startswith(expected_header)
    assert expected_self_desc in result
    assert result.find(expected_header) < result.find(expected_self_desc)


def test_footer_injection(tmp_path):
    """Verifies that the footer is correctly injected."""
    db = tmp_path / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    constitution = "Core rules."
    result = spawn.inject_identity(constitution, "test-role", "test-agent")

    expected_footer = "run `space` for orientation (already in PATH).\nrun: `memory --as test-agent` to access memories."

    assert expected_footer in result
    assert result.endswith(expected_footer)


def test_canon_injection_order(tmp_path):
    """Verifies that canon is injected before the base constitution content."""
    db = tmp_path / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# CANON\n1. Truth")

    constitution = "Core rules."
    result = spawn.inject_identity(constitution, "test-role", "test-agent")

    lines = result.split("\n")
    header_idx = next(i for i, line in enumerate(lines) if "# TEST-ROLE CONSTITUTION" in line)
    self_desc_idx = next(i for i, line in enumerate(lines) if "Self: You are test-agent." in line)
    canon_idx = next(i for i, line in enumerate(lines) if "# CANON" in line)
    constitution_idx = next(i for i, line in enumerate(lines) if "Core rules." in line)
    footer_idx = next(i for i, line in enumerate(lines) if "run `space`" in line)

    assert header_idx < self_desc_idx < canon_idx < constitution_idx < footer_idx
