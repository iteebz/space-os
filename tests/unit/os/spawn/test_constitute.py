"""Tests for spawn constitution setup."""

from unittest.mock import MagicMock, patch

import pytest

from space.core.models import Spawn, SpawnStatus
from space.os.spawn.constitute import PROVIDER_MAP, constitute


@pytest.fixture
def agent():
    """Mock agent."""
    agent = MagicMock()
    agent.identity = "zealot"
    agent.constitution = "zealot.md"
    agent.provider = "claude"
    return agent


@pytest.fixture
def spawn():
    """Ephemeral spawn."""
    return Spawn(id="spawn-1", agent_id="agent-1", status=SpawnStatus.PENDING)


def test_constitute_writes_to_identity_dir(tmp_path, spawn, agent):
    """Spawn writes constitution to ~/.space/spawns/{identity}/."""
    spawns_dir = tmp_path / "spawns" / "zealot"
    with patch("space.lib.paths.identity_dir", return_value=spawns_dir):
        with patch("space.lib.paths.constitution") as mock_const_path:
            const_file = tmp_path / "zealot.md"
            const_file.write_text("# Zealot")
            mock_const_path.return_value = const_file

            result = constitute(spawn, agent)

            assert result == spawns_dir
            assert (spawns_dir / "CLAUDE.md").exists()
            assert (spawns_dir / "CLAUDE.md").read_text() == "# Zealot"


def test_constitute_no_constitution(tmp_path, spawn, agent):
    """Spawn without constitution still creates directory."""
    agent.constitution = None
    spawns_dir = tmp_path / "spawns" / "zealot"
    with patch("space.lib.paths.identity_dir", return_value=spawns_dir):
        result = constitute(spawn, agent)
        assert result == spawns_dir
        assert spawns_dir.exists()


def test_constitute_provider_map():
    """PROVIDER_MAP has correct filenames."""
    assert PROVIDER_MAP["claude"] == "CLAUDE.md"
    assert PROVIDER_MAP["gemini"] == "GEMINI.md"
    assert PROVIDER_MAP["codex"] == "AGENTS.md"
