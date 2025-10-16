"""Integration test: Invocation context and constitution provenance."""

from typer.testing import CliRunner

from space.cli import app
from space.lib.invocation import AliasResolver, InvocationContext

runner = CliRunner()


def test_invocation_context_tracks_identity(test_space):
    """Verify: InvocationContext captures identity from --as flag."""
    ctx = InvocationContext.from_args(["wake", "--as", "test-agent"])
    assert ctx.identity == "test-agent"
    assert ctx.command == "wake"


def test_alias_resolver_normalizes_wake_identity(test_space):
    """Verify: AliasResolver rewrites wake identity positional arg."""
    result = AliasResolver.normalize_args(["wake", "my-agent"])
    assert result == ["wake", "--as", "my-agent"]


def test_alias_resolver_preserves_explicit_flag(test_space):
    """Verify: AliasResolver doesn't double-wrap --as."""
    result = AliasResolver.normalize_args(["wake", "--as", "my-agent"])
    assert result == ["wake", "--as", "my-agent"]


def test_wake_explicit_flag_invocation(test_space):
    """Verify: wake --as agent works end-to-end."""
    result = runner.invoke(app, ["wake", "--as", "explicit-agent"])
    assert result.exit_code == 0
    assert "explicit-agent" in result.stdout or "Spawn" in result.stdout


def test_constitution_hash_content_addressable(test_space):
    """Verify: constitution hash is computed from content."""
    from space.spawn import spawn

    test_content = "# TEST CONSTITUTION\nTest identity marker"
    test_hash = spawn.hash_content(test_content)

    assert len(test_hash) == 64, "SHA256 hash should be 64 hex chars"
    assert test_hash.isalnum(), "Hash should be alphanumeric"


def test_invocation_context_emits_with_agent_id(test_space):
    """Verify: InvocationContext resolves agent_id for telemetry."""
    from space.spawn import registry

    registry.init_db()
    registry.ensure_agent("telemetry-test-agent")

    ctx = InvocationContext.from_args(["wake", "--as", "telemetry-test-agent"])
    assert ctx.agent_id is not None
    assert isinstance(ctx.agent_id, str)
