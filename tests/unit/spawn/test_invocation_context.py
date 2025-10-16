"""Test invocation context system for CLI telemetry and aliases."""

from typer.testing import CliRunner

from space.events import query
from space.lib.invocation import InvocationContext

runner = CliRunner()


def test_invocation_context_tracks_identity(test_space):
    """Invocation context captures identity from --as flag."""
    ctx = InvocationContext.from_args(["wake", "--as", "test-agent"])
    assert ctx.identity == "test-agent"
    assert ctx.command == "wake"


def test_invocation_context_parses_command(test_space):
    """Invocation context extracts command name."""
    ctx = InvocationContext.from_args(["memory", "list"])
    assert ctx.command == "memory"
    assert ctx.subcommand == "list"


def test_invocation_context_no_identity(test_space):
    """Invocation context handles missing identity."""
    ctx = InvocationContext.from_args(["wake"])
    assert ctx.identity is None
    assert ctx.command == "wake"


def test_invocation_context_emits_to_events(test_space):
    """Invocation context can emit to events system."""
    ctx = InvocationContext(
        command="wake",
        identity="test-agent",
        full_args=["wake", "--as", "test-agent"],
        subcommand=None,
    )
    ctx.emit_invocation()

    events = query(source="cli", limit=1)
    assert len(events) > 0
    event = events[0]
    assert event[3] == "invocation"


def test_invocation_context_preserves_original_args(test_space):
    """Invocation context stores original argv for debugging."""
    args = ["wake", "--as", "test-agent", "--extra"]
    ctx = InvocationContext.from_args(args)
    assert ctx.full_args == args
