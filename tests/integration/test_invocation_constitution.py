"""Integration test: Invocation context and constitution provenance."""

from unittest.mock import patch

from typer.testing import CliRunner

from space.app import app
from space.lib.invocation import Invocation

runner = CliRunner()


def test_invocation_context_tracks_identity(test_space):
    ctx = Invocation.from_args(["wake", "--as", "test-agent"])
    assert ctx.identity == "test-agent"
    assert ctx.command == "wake"


def test_alias_resolver_normalizes_wake_identity(test_space):
    from space.lib.aliasing import Aliasing

    result = Aliasing.normalize_args(["wake", "my-agent"])
    assert result == ["wake", "--as", "my-agent"]


def test_alias_resolver_preserves_explicit_flag(test_space):
    from space.lib.aliasing import Aliasing

    result = Aliasing.normalize_args(["wake", "--as", "my-agent"])
    assert result == ["wake", "--as", "my-agent"]


def test_wake_explicit_flag_invocation(test_space):
    with patch("space.lib.sessions.sync"):
        result = runner.invoke(app, ["wake", "--as", "explicit-agent"])
        assert result.exit_code == 0
        assert "explicit-agent" in result.stdout or "Spawn" in result.stdout


def test_constitution_hash_content_addressable(test_space):
    from space.spawn import spawn

    test_content = "# TEST CONSTITUTION\nTest identity marker"
    test_hash = spawn.hash_content(test_content)

    assert len(test_hash) == 64, "SHA256 hash should be 64 hex chars"
    assert test_hash.isalnum(), "Hash should be alphanumeric"


def test_invocation_context_emits_with_agent_id(test_space):
    from space.spawn import registry

    registry.init_db()
    registry.ensure_agent("telemetry-test-agent")

    ctx = Invocation.from_args(["wake", "--as", "telemetry-test-agent"])
    assert ctx.agent_id is not None
    assert isinstance(ctx.agent_id, str)
