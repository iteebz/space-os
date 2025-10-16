from pathlib import Path

import pytest
import yaml

from space.lib import paths
from space.spawn import spawn


@pytest.fixture
def mock_config_files(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(paths, "space_root", lambda base_path=None: tmp_path)

    # Create dummy config.yaml
    config_content = {
        "agents": {"gemini": {"command": "gemini", "model": "gemini-2.5-pro"}},
        "roles": {"crucible": {"constitution": "crucible.md", "base_identity": "gemini"}},
    }
    config_dir = tmp_path / "space"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump(config_content))
    constitutions_dir = config_dir / "constitutions"
    constitutions_dir.mkdir()
    (constitutions_dir / "kitsuragi.md").write_text("# LIEUTENANT KIM KITSURAGI")

    # Create dummy crucible.md
    constitutions_dir = tmp_path / "space" / "constitutions"
    constitutions_dir.mkdir(exist_ok=True)
    (constitutions_dir / "crucible.md").write_text("**YOU ARE NOW CRUCIBLE.**")

    # Mock config_file to point to the dummy config
    monkeypatch.setattr(spawn.config, "config_file", lambda: config_dir / "config.yaml")
    monkeypatch.setattr(spawn.shutil, "which", lambda cmd, path=None: cmd)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)


def test_constitution_message(mock_config_files, tmp_path: Path, monkeypatch):
    # Mock registry functions to avoid database interaction for this test
    monkeypatch.setattr(spawn.registry, "init_db", lambda: None)
    monkeypatch.setattr(spawn.registry, "get_self_description", lambda agent_name: None)
    monkeypatch.setattr(spawn.registry, "save_constitution", lambda const_hash, full_identity: None)

    # Simulate the call from cli.py after the fix
    # The cli.py now passes 'arg' (role name) as agent_name
    spawn.launch_agent(
        role="crucible",
        identity="crucible",  # This is the key change being tested
        base_identity="gemini",  # This comes from the --as flag or default
        extra_args=[],
        model="gemini-2.5-pro",  # This comes from the --model flag or default
    )

    # Read the generated identity file
    identity_file_path = tmp_path / "GEMINI.md"  # Because base_identity for crucible is gemini
    assert identity_file_path.exists()
    content = identity_file_path.read_text()

    # Assert the expected identity message
    expected_constitution = "**YOU ARE NOW CRUCIBLE.**"
    assert "# CRUCIBLE CONSTITUTION" in content
    assert "Self: You are crucible. Your model is gemini-2.5-pro." in content
    assert expected_constitution in content
    assert "run `space` for orientation (already in PATH)." in content
    assert "run: `memory --as crucible` to access memories." in content


def test_codex_writes_agents_manifest(tmp_path: Path, monkeypatch):
    # Wire workspace to temporary location
    monkeypatch.setattr(paths, "space_root", lambda base_path=None: tmp_path)

    config_content = {
        "agents": {"codex": {"command": "codex", "model": "gpt-5-codex"}},
        "roles": {"kitsuragi": {"constitution": "kitsuragi.md", "base_identity": "codex"}},
    }
    config_dir = tmp_path / "space"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump(config_content))

    monkeypatch.setattr(spawn.config, "config_file", lambda: config_dir / "config.yaml")
    monkeypatch.setattr(spawn.shutil, "which", lambda cmd, path=None: cmd)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    # Mock registry access
    monkeypatch.setattr(spawn.registry, "init_db", lambda: None)
    monkeypatch.setattr(spawn.registry, "get_self_description", lambda agent_name: None)
    monkeypatch.setattr(spawn.registry, "save_constitution", lambda const_hash, full_identity: None)

    spawn.launch_agent(
        role="kitsuragi",
        identity="kitsuragi",
        base_identity="codex",
        extra_args=[],
        model="gpt-5-codex",
    )

    codex_file = tmp_path / "AGENTS.md"
    content = codex_file.read_text()
    assert "# KITSURAGI CONSTITUTION" in content
    assert "Self: You are kitsuragi. Your model is gpt-5-codex." in content
    assert "# LIEUTENANT KIM KITSURAGI" in content
    assert "run `space` for orientation (already in PATH)." in content
    assert "run: `memory --as kitsuragi` to access memories." in content


def test_hailot_prompt_constitution(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(paths, "space_root", lambda base_path=None: tmp_path)

    prompts_dir = tmp_path / "canon" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "zealot.md").write_text(
        "**YOU ARE NOW A ZEALOT.**\n\n## CORE PRINCIPLES\nHelpfulness = Skeptical partner."
    )

    monkeypatch.setattr(paths, "canon_path", lambda base_path=None: tmp_path / "canon")

    config_content = {
        "agents": {"haiku": {"command": "claude", "model": "claude-haiku-4-5"}},
        "roles": {"hailot": {"constitution": "zealot.md", "base_identity": "haiku"}},
    }
    config_dir = tmp_path / "space"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump(config_content))

    monkeypatch.setattr(spawn.config, "config_file", lambda: config_dir / "config.yaml")
    monkeypatch.setattr(spawn.shutil, "which", lambda cmd, path=None: cmd)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)

    monkeypatch.setattr(spawn.registry, "init_db", lambda: None)
    monkeypatch.setattr(spawn.registry, "get_self_description", lambda agent_name: None)
    monkeypatch.setattr(spawn.registry, "save_constitution", lambda const_hash, full_identity: None)

    spawn.launch_agent(
        role="hailot",
        identity="hailot",
        base_identity="haiku",
        extra_args=[],
        model="claude-haiku-4-5",
    )

    claude_file = tmp_path / "CLAUDE.md"
    content = claude_file.read_text()
    assert "# HAILOT CONSTITUTION" in content
    assert "Self: You are hailot. Your model is claude-haiku-4-5." in content
    assert "**YOU ARE NOW A ZEALOT.**" in content
    assert "run `space` for orientation (already in PATH)." in content
    assert "run: `memory --as hailot` to access memories." in content
