from typer.testing import CliRunner

from space.cli import app
from space.events import query

runner = CliRunner()


def test_cli_invocation(test_space):
    """Verify all CLI invocations are logged to events."""
    runner.invoke(app, ["wake", "--as", "test-agent"])

    events = query(source="cli", limit=1)
    assert len(events) == 1

    event = events[0]
    assert event[1] == "cli"
    assert event[3] == "invocation"
    assert event[4] is not None


def test_cli_no_command(test_space):
    """Verify no command invocation is logged."""
    runner.invoke(app, [])

    events = query(source="cli", limit=1)
    assert len(events) == 1

    event = events[0]
    assert event[1] == "cli"
    assert event[3] == "invocation"
