"""Integration test: CLI constitution provenance."""

from unittest.mock import patch

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_wake_explicit_flag(test_space):
    """CLI wake with --as flag runs without sync."""
    with patch("space.os.lib.chats.sync"):
        result = runner.invoke(app, ["wake", "--as", "explicit-agent"])
        assert result.exit_code == 0
        assert "explicit-agent" in result.stdout or "Spawn" in result.stdout


def test_agent_id_resolution(test_space):
    """Resolve agent name to UUID."""
    from space.os import spawn

    spawn.db.ensure_agent("telemetry-test-agent")
    agent_id = spawn.db.get_agent_id("telemetry-test-agent")
    assert agent_id is not None
    assert isinstance(agent_id, str)
