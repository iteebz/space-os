import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from space.spawn import registry


@pytest.fixture
def setup_test_spawn_db(tmp_path):
    """Set up a temporary spawn.db with multiple identity entries."""
    test_db_path = tmp_path / "spawn.db"
    # Patch the registry_db path to use our temporary db
    with patch("space.spawn.config.registry_db", return_value=test_db_path):
        registry.init_db()

        # Add multiple entries for 'test_evo_agent'
        registry.register(
            role="test_role",
            agent_id="test_evo_agent",
            channels=["test-channel"],
            identity_hash="hash_evo_1",
            identity="Content of version 1",
        )
        registry.register(
            role="test_role",
            agent_id="test_evo_agent",
            channels=["test-channel"],
            identity_hash="hash_evo_2",
            identity="Content of version 2",
        )
        registry.register(
            role="test_role",
            agent_id="test_evo_agent",
            channels=["test-channel"],
            identity_hash="hash_evo_3",
            identity="Content of version 3",
        )
        # Add a single entry for 'test_get_agent'
        registry.register(
            role="test_role_get",
            agent_id="test_get_agent",
            channels=["test-channel"],
            identity_hash="hash_get_latest",
            identity="Latest content for get agent",
        )
        yield test_db_path


@pytest.fixture
def cli_runner(tmp_path):
    """Fixture to run CLI commands in a controlled environment."""
    # Ensure the poetry environment is used
    poetry_env = os.environ.copy()
    poetry_env["PYTHONPATH"] = str(
        Path(__file__).parent.parent.parent.parent
    )  # Point to agent-space root

    def _run_cli(command_args, db_path):
        # Temporarily set the workspace root to ensure config.registry_db() points to our test db
        with patch("space.spawn.config.registry_db", return_value=db_path):
            cmd = ["poetry", "run", "python", "-m", "space.spawn.cli"] + command_args
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't raise exception for non-zero exit codes
                env=poetry_env,
                cwd=str(Path(__file__).parent.parent.parent.parent),  # Run from agent-space root
            )

    return _run_cli


def test_identity_evo_displays_chronological_history(setup_test_spawn_db, cli_runner):
    """Verify 'spawn identity evo' displays chronological history."""
    result = cli_runner(["identity", "evo", "--as", "test_evo_agent"], setup_test_spawn_db)

    assert result.returncode == 0
    assert "--- Registered At: 2023-01-01 10:00:00 ---" in result.stdout
    assert "--- Constitution Hash: hash_evo_1 ---" in result.stdout
    assert "Content of version 1" in result.stdout
    assert "--- Registered At: 2023-01-01 11:00:00 ---" in result.stdout
    assert "--- Constitution Hash: hash_evo_2 ---" in result.stdout
    assert "Content of version 2" in result.stdout
    assert "--- Registered At: 2023-01-01 12:00:00 ---" in result.stdout
    assert "--- Constitution Hash: hash_evo_3 ---" in result.stdout
    assert "Content of version 3" in result.stdout

    # Verify chronological order
    output_lines = result.stdout.splitlines()
    timestamps = []
    for line in output_lines:
        if "--- Registered At:" in line:
            timestamps.append(line.split("Registered At: ")[1].split(" ---")[0])

    assert timestamps == ["2023-01-01 10:00:00", "2023-01-01 11:00:00", "2023-01-01 12:00:00"]


def test_identity_get_retrieves_latest_constitution(setup_test_spawn_db, cli_runner):
    """Verify 'spawn identity get' retrieves the latest constitution content."""
    result = cli_runner(["identity", "get", "--as", "test_get_agent"], setup_test_spawn_db)

    assert result.returncode == 0
    assert "Latest content for get agent" in result.stdout
    assert "hash_get_latest" not in result.stdout  # Should only show content, not hash
    assert "Registered At" not in result.stdout  # Should only show content, not timestamp


def test_identity_get_non_existent_agent(setup_test_spawn_db, cli_runner):
    """Verify 'spawn identity get' handles non-existent agents."""
    result = cli_runner(["identity", "get", "--as", "non_existent_agent"], setup_test_spawn_db)

    assert result.returncode == 1
    assert "Error: Identity 'non_existent_agent' not found in registry." in result.stderr
