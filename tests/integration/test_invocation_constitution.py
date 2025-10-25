"""Integration test: Invocation context and constitution provenance."""

from unittest.mock import patch

from typer.testing import CliRunner

from space.cli import app
from space.os.lib.invocation import Invocation

runner = CliRunner()


def test_invocation_context_tracks_identity(test_space):
    """Parse CLI args to extract identity and command."""
    ctx = Invocation.from_args(["wake", "--as", "test-agent"])
    assert ctx.identity == "test-agent"
    assert ctx.command == "wake"


def test_alias_normalize_wake(test_space):
    """Rewrite positional agent to --as flag."""
    from space.os.lib.aliasing import Aliasing

    result = Aliasing.rewrite(["wake", "my-agent"])
    assert result == ["wake", "--as", "my-agent"]


def test_alias_preserve_flag(test_space):
    """Keep explicit --as flag unchanged."""
    from space.os.lib.aliasing import Aliasing

    result = Aliasing.rewrite(["wake", "--as", "my-agent"])
    assert result == ["wake", "--as", "my-agent"]


def test_wake_explicit_flag_invocation(test_space):
    """CLI wake with --as flag runs without sync."""
    with patch("space.os.lib.chats.sync"):
        result = runner.invoke(app, ["wake", "--as", "explicit-agent"])
        assert result.exit_code == 0
        assert "explicit-agent" in result.stdout or "Spawn" in result.stdout


def test_constitution_hash_addressable(test_space):
    """Hash content produces valid SHA256."""
    from space.os.core.spawn.spawn import hash_content

    test_content = "# TEST CONSTITUTION\nTest identity marker"
    test_hash = hash_content(test_content)

    assert len(test_hash) == 64
    assert test_hash.isalnum()


def test_invocation_agent_id(test_space):
    """Resolve agent name to UUID via invocation context."""
    from space.os import spawn

    spawn.db.ensure_agent("telemetry-test-agent")

    ctx = Invocation.from_args(["wake", "--as", "telemetry-test-agent"])
    assert ctx.agent_id is not None
    assert isinstance(ctx.agent_id, str)
