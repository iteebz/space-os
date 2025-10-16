from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_first_spawn_initiation(test_space):
    """First spawn shows initiation flow."""
    result = runner.invoke(app, ["wake", "--as", "new-agent"])

    assert result.exit_code == 0
    assert "Spawn #0" in result.stdout
    assert "Explore autonomously" in result.stdout


def test_second_spawn_increments_count(test_space):
    """Second wake for same agent increments spawn counter."""
    agent = "existing-agent"

    first = runner.invoke(app, ["wake", "--as", agent])
    assert "Spawn #0" in first.stdout

    second = runner.invoke(app, ["wake", "--as", agent])
    assert "Spawn #1" in second.stdout or "Spawn" in second.stdout


def test_session_auto_closes_on_new_wake(test_space):
    """New wake auto-closes previous session."""
    from space import events
    from space.spawn import registry

    agent = "session-test-agent"

    runner.invoke(app, ["wake", "--as", agent])
    agent_id = registry.get_agent_id(agent)

    runner.invoke(app, ["wake", "--as", agent])

    session_events = events.query(source="session", agent_id=agent_id)
    start_events = [e for e in session_events if e.event_type == "session_start"]
    end_events = [e for e in session_events if e.event_type == "session_end"]

    assert len(start_events) >= 2
    assert len(end_events) >= 1
    auto_closed = [e for e in end_events if e.data == "auto_closed"]
    assert len(auto_closed) >= 1
