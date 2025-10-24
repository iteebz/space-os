from space.os.spawn import registry, spawn


def test_header_injection(tmp_path):
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
    db = tmp_path / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    constitution = "Core rules."
    result = spawn.inject_identity(constitution, "test-role", "test-agent")

    expected_footer = "run `space` for orientation (already in PATH).\nrun: `memory --as test-agent` to access memories."

    assert expected_footer in result
    assert result.endswith(expected_footer)


def test_canon_injection_order(mocker, tmp_path):
    db = tmp_path / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    canon_dir = tmp_path / "canon"
    canon_dir.mkdir(parents=True, exist_ok=True)
    (canon_dir / "test_canon.md").write_text("# CANON\n1. Truth")
    mocker.patch("space.os.lib.paths.canon_path", return_value=canon_dir)

    constitution = "Core rules."
    result = spawn.inject_identity(constitution, "test-role", "test-agent")

    assert "# CANON" not in result
    assert "1. Truth" not in result
