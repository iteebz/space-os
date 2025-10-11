from pathlib import Path

import pytest
import yaml

from space.lib import paths
from space.spawn import spawn


@pytest.fixture
def mock_config_files(tmp_path: Path, monkeypatch):
    # Mock workspace_root to point to tmp_path
    monkeypatch.setattr(paths, "workspace_root", lambda: tmp_path)

    # Create dummy config.yaml
    config_content = {
        "agents": {"gemini": {"command": "gemini", "model": "gemini-2.5-pro"}},
        "roles": {"crucible": {"constitution": "crucible.md", "base_identity": "gemini"}},
    }
    config_dir = tmp_path / "space"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(yaml.dump(config_content))

    # Create dummy crucible.md
    constitutions_dir = tmp_path / "space" / "constitutions"
    constitutions_dir.mkdir()
    (constitutions_dir / "crucible.md").write_text("**YOU ARE NOW CRUCIBLE.**")

    # Mock config_file to point to the dummy config
    monkeypatch.setattr(spawn.config, "config_file", lambda: str(config_dir / "config.yaml"))


def test_crucible_identity_message(mock_config_files, tmp_path: Path, monkeypatch):
    # Mock registry functions to avoid database interaction for this test
    monkeypatch.setattr(spawn.registry, "init_db", lambda: None)
    monkeypatch.setattr(spawn.registry, "get_self_description", lambda agent_name: None)
    monkeypatch.setattr(spawn.registry, "save_constitution", lambda const_hash, full_identity: None)

    # Simulate the call from cli.py after the fix
    # The cli.py now passes 'arg' (role name) as agent_name
    spawn.launch_agent(
        role="crucible",
        agent_name="crucible",  # This is the key change being tested
        base_identity="gemini",  # This comes from the --as flag or default
        extra_args=[],
        model="gemini-2.5-pro",  # This comes from the --model flag or default
    )

    # Read the generated identity file
    identity_file_path = tmp_path / "GEMINI.md"  # Because base_identity for crucible is gemini
    assert identity_file_path.exists()
    content = identity_file_path.read_text()

    # Assert the expected identity message
    expected_header = "You are now crucible powered by gemini-2.5-pro."
    expected_constitution = "**YOU ARE NOW CRUCIBLE.**"
    assert expected_header in content
    assert expected_constitution in content
    assert "Infrastructure: run `space` for commands and orientation (already in PATH)." in content
