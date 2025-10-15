import json
from unittest.mock import patch

from space.lib import identity
from space.spawn import registry, spawn


def test_inject_no_self(mocker, tmp_path):
    dot_space = tmp_path / ".space"
    dot_space.mkdir()
    mocker.patch("space.lib.paths.dot_space", return_value=dot_space)
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    (canon_dir / "test_canon.md").write_text("# CANON")
    mocker.patch("space.lib.paths.canon_path", return_value=canon_dir)
    db = dot_space / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    const = "You are a sentinel."
    result = spawn.inject_identity(const, "sentinel", "sentinel")

    assert "# SENTINEL CONSTITUTION" in result
    assert "Self: You are sentinel." in result
    assert "You are a sentinel." in result
    canon_dir.mkdir(exist_ok=True)
    (canon_dir / "test_canon.md").write_text("# CANON")
    mocker.patch("space.lib.paths.canon_path", return_value=canon_dir)
    db = dot_space / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    registry.set_self_description("sentinel-1", "Reality guardian")

    const = "You are a sentinel."
    result = spawn.inject_identity(const, "sentinel", "sentinel-1")

    assert "# SENTINEL CONSTITUTION" in result
    assert "Self: You are sentinel-1." in result
    assert "You are a sentinel." in result
    assert "# CANON" in result


def test_evolution(mocker, tmp_path):
    dot_space = tmp_path / ".space"
    dot_space.mkdir()
    mocker.patch("space.lib.paths.dot_space", return_value=dot_space)
    db = dot_space / "spawn.db"
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


def test_describe_updates_self(mocker, tmp_path):
    dot_space = tmp_path / ".space"
    dot_space.mkdir()
    mocker.patch("space.lib.paths.dot_space", return_value=dot_space)
    db = dot_space / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    updated = registry.set_self_description("scribe-1", "Voice of the council")
    desc = registry.get_self_description("scribe-1")

    assert updated
    assert desc == "Voice of the council"


def test_inject_with_model(mocker, tmp_path):
    dot_space = tmp_path / ".space"
    dot_space.mkdir()
    mocker.patch("space.lib.paths.dot_space", return_value=dot_space)
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    (canon_dir / "test_canon.md").write_text("# CANON")
    mocker.patch("space.lib.paths.canon_path", return_value=canon_dir)
    db = dot_space / "spawn.db"
    registry.config.registry_db = lambda: db
    registry.init_db()

    const = "You are a zealot."
    result = spawn.inject_identity(const, "zealot", "zealot-1", "claude-sonnet-4.5")

    assert "# ZEALOT CONSTITUTION" in result
    assert "Self: You are zealot-1. Your model is claude-sonnet-4.5." in result
    assert "You are a zealot." in result
    assert "# CANON" in result


def test_constitute_identity_emits_correct_event_source(mocker, tmp_path):
    # Setup mock environment
    dot_space = tmp_path / ".space"
    dot_space.mkdir()
    mocker.patch("space.lib.paths.dot_space", return_value=dot_space)
    mocker.patch("space.spawn.config.config_file", return_value=tmp_path / "config.yaml")

    # Create a dummy config.yaml
    config_content = {
        "agents": {"gemini": {"command": "gemini", "model": "gemini-2.5-pro"}},
        "roles": {"harbinger": {"constitution": "harbinger.md", "base_identity": "gemini"}},
    }
    with open(tmp_path / "config.yaml", "w") as f:
        json.dump(config_content, f)

    # Create a dummy constitution file
    constitutions_dir = tmp_path / "constitutions"
    constitutions_dir.mkdir()
    (constitutions_dir / "harbinger.md").write_text("# HARBINGER CONSTITUTION")
    mocker.patch("space.lib.paths.constitution", return_value=constitutions_dir / "harbinger.md")

    # Mock registry and events
    mocker.patch.object(registry, "init_db")
    mocker.patch.object(registry, "ensure_agent", return_value="test-agent-uuid")
    mocker.patch.object(registry, "save_constitution")
    mocker.patch.object(spawn, "load_config", return_value=config_content)
    mocker.patch.object(
        spawn, "get_constitution_path", return_value=constitutions_dir / "harbinger.md"
    )
    mocker.patch.object(spawn, "inject_identity", return_value="full-identity-content")
    mocker.patch.object(spawn, "hash_content", return_value="test-hash")

    with patch("space.events.emit") as mock_emit:
        identity.constitute_identity("harbinger-1", event_source="bridge")

        mock_emit.assert_called_once()
        # Assert that the event was emitted with the correct source
        assert mock_emit.call_args[0][0] == "bridge"
        assert mock_emit.call_args[0][1] == "constitution_invoked"
        assert mock_emit.call_args[0][2] == "test-agent-uuid"
