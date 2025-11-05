"""Tests for spawn constitution setup."""

from unittest.mock import MagicMock, patch

import pytest

from space.core.models import Spawn, SpawnStatus
from space.os.spawn.api.constitute import PROVIDER_MAP, constitute


@pytest.fixture
def agent():
    """Mock agent."""
    agent = MagicMock()
    agent.identity = "zealot"
    agent.constitution = "zealot.md"
    agent.provider = "claude"
    return agent


@pytest.fixture
def spawn_interactive():
    """Interactive spawn (is_ephemeral=False)."""
    return Spawn(id="spawn-1", agent_id="agent-1", is_ephemeral=False, status=SpawnStatus.PENDING)


@pytest.fixture
def spawn_headless():
    """Headless spawn (is_ephemeral=True)."""
    return Spawn(id="spawn-2", agent_id="agent-1", is_ephemeral=True, status=SpawnStatus.PENDING)


def test_constitute_interactive_writes_to_space_root(tmp_path, spawn_interactive, agent):
    """Interactive spawn writes constitution to ~/space/."""
    with patch("space.lib.paths.space_root", return_value=tmp_path):
        with patch("space.lib.paths.constitution") as mock_const_path:
            const_file = tmp_path / "zealot.md"
            const_file.write_text("# Zealot")
            mock_const_path.return_value = const_file

            result = constitute(spawn_interactive, agent)

            assert result == tmp_path
            assert (tmp_path / "CLAUDE.md").exists()
            assert (tmp_path / "CLAUDE.md").read_text() == "# Zealot"


def test_constitute_headless_writes_to_spawns_dir(tmp_path, spawn_headless, agent):
    """Headless spawn writes constitution to ~/.space/spawns/{identity}/."""
    spawns_dir = tmp_path / "spawns" / "zealot"
    with patch("space.lib.paths.identity_dir", return_value=spawns_dir):
        with patch("space.lib.paths.constitution") as mock_const_path:
            const_file = tmp_path / "zealot.md"
            const_file.write_text("# Zealot")
            mock_const_path.return_value = const_file

            result = constitute(spawn_headless, agent)

            assert result == spawns_dir
            assert (spawns_dir / "CLAUDE.md").exists()
            assert (spawns_dir / "CLAUDE.md").read_text() == "# Zealot"


def test_constitute_no_constitution(tmp_path, spawn_interactive, agent):
    """Spawn without constitution still creates directory."""
    agent.constitution = None
    with patch("space.lib.paths.space_root", return_value=tmp_path):
        result = constitute(spawn_interactive, agent)
        assert result == tmp_path
        assert tmp_path.exists()


def test_constitute_provider_map():
    """PROVIDER_MAP has correct filenames."""
    assert PROVIDER_MAP["claude"] == "CLAUDE.md"
    assert PROVIDER_MAP["gemini"] == "GEMINI.md"
    assert PROVIDER_MAP["codex"] == "AGENTS.md"
