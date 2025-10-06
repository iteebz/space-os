from pathlib import Path
from unittest.mock import patch

import pytest

from space.spawn import spawner
from space.spawn.registry import Registration  # Import Registration directly


@pytest.fixture
def mock_config_file(tmp_path):
    """Create a mock config.yaml for testing."""
    config_content = """
roles:
  test_role:
    constitution: constitutions/test_constitution.md
    base_identity: test_agent
agents:
  test_agent:
    command: echo hello
    constitution_arg: --constitution-file
"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(config_content)
    with patch("space.spawn.config.CONFIG_FILE", new=config_path):
        yield


@pytest.fixture
def mock_constitution_file(tmp_path):
    """Create a mock constitution file."""
    const_dir = tmp_path / "constitutions"
    const_dir.mkdir()
    const_path = const_dir / "test_constitution.md"
    const_path.write_text("You are a test agent.")
    with patch("space.spawn.config.CONSTITUTIONS_DIR", new=const_dir):
        yield


def test_launch_agent_sets_constitution_hash_env(mock_config_file, mock_constitution_file):
    """Verify AGENT_CONSTITUTION_HASH is set in environment when launching agent."""
    mock_reg = Registration(
        id=1,
        role="test_role",
        sender_id="test_sender",
        topic="test_topic",
        identity_hash="mock_constitution_hash_123",
        identity="You are a test agent.",
        registered_at="2023-01-01",
        self=None,
        model=None,
        notes=None,
    )

    with (
        patch("space.spawn.registry.get_registration", return_value=mock_reg),
        patch("subprocess.run") as mock_subprocess_run,
        patch("space.spawn.config.workspace_root", return_value=Path("/mock/workspace")),
    ):
        spawner.launch_agent(
            role="test_role", agent="test_agent", extra_args=[], model="test_model"
        )

        mock_subprocess_run.assert_called_once()
        # Check the env argument passed to subprocess.run
        call_args, call_kwargs = mock_subprocess_run.call_args
        env = call_kwargs.get("env")

        assert env is not None
        assert env.get("AGENT_CONSTITUTION_HASH") == "mock_constitution_hash_123"
        assert env.get("AGENT_MODEL") == "test_model"
        assert env.get("PWD") == "/mock/workspace"
