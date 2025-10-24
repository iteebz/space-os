"""Test invocation context system for CLI telemetry and aliases."""

from typer.testing import CliRunner

from space.os.events import query
from space.os.lib.invocation import Invocation

runner = CliRunner()


def test_tracks_identity(test_space):
    ctx = Invocation.from_args(["wake", "--as", "test-agent"])
    assert ctx.identity == "test-agent"
    assert ctx.command == "wake"


def test_parses_command(test_space):
    ctx = Invocation.from_args(["memory", "list"])
    assert ctx.command == "memory"
    assert ctx.subcommand == "list"


def test_no_identity(test_space):
    ctx = Invocation.from_args(["wake"])
    assert ctx.identity is None
    assert ctx.command == "wake"


def test_emits_to_events(test_space):
    ctx = Invocation(
        command="wake",
        identity="test-agent",
        full_args=["wake", "--as", "test-agent"],
        subcommand=None,
    )
    ctx.emit_invocation()

    events = query(source="cli", limit=1)
    assert len(events) > 0
    event = events[0]
    assert event.event_type == "invocation"


def test_preserves_original_args(test_space):
    args = ["wake", "--as", "test-agent", "--extra"]
    ctx = Invocation.from_args(args)
    assert ctx.full_args == args
