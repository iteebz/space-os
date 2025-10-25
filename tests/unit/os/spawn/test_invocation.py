"""Test invocation context system for CLI telemetry and aliases."""

from space.os.events import query
from space.os.lib.invocation import Invocation


def test_parse_identity():
    ctx = Invocation.from_args(["wake", "--as", "test-agent"])
    assert ctx.identity == "test-agent"
    assert ctx.command == "wake"


def test_parse_subcommand():
    ctx = Invocation.from_args(["memory", "list"])
    assert ctx.command == "memory"
    assert ctx.subcommand == "list"


def test_parse_no_identity():
    ctx = Invocation.from_args(["wake"])
    assert ctx.identity is None
    assert ctx.command == "wake"


def test_emit_invocation(test_space):
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
