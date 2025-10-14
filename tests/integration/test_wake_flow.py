import pytest
from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_db(test_space):
    pass


def test_first_spawn_initiation():
    """First spawn shows initiation flow."""
    result = runner.invoke(app, ["wake", "--as", "new-agent"])

    assert result.exit_code == 0
    assert "🔄 Spawn #0" in result.stdout

    assert "Explore autonomously" in result.stdout


def test_second_spawn_orientation():
    """Subsequent spawns show standard orientation."""
    agent = "existing-agent"

    first = runner.invoke(app, ["wake", "--as", agent])
    assert "🔄 Spawn #0" in first.stdout

    second = runner.invoke(app, ["wake", "--as", agent])
    assert "Spawn #0" in second.stdout
    assert "Explore autonomously" in second.stdout


def test_session_auto_closes_previous():
    """New wake auto-closes previous session without sleep."""
    from space import events
    from space.spawn import registry

    agent = "session-test-agent"

    runner.invoke(app, ["wake", "--as", agent])
    agent_id = registry.get_agent_id(agent)

    # This is now 0 because we count sleep events
    assert events.get_sleep_count(agent_id) == 0

    session_events = events.query(source="session", agent_id=agent_id)
    assert len([e for e in session_events if e[3] == "session_start"]) == 1
    assert len([e for e in session_events if e[3] == "session_end"]) == 0

    runner.invoke(app, ["wake", "--as", agent])

    # This is still 0
    assert events.get_sleep_count(agent_id) == 0

    session_events = events.query(source="session", agent_id=agent_id)
    start_events = [e for e in session_events if e[3] == "session_start"]
    end_events = [e for e in session_events if e[3] == "session_end"]

    assert len(start_events) == 2
    assert len(end_events) == 1
    assert end_events[0][4] == "auto_closed"
