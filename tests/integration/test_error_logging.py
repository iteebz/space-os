"""Integration tests for error logging - ensures regressions are caught."""

import sqlite3

from typer.testing import CliRunner

from space import events
from space.cli import app as space_app
from space.lib import paths
from space.spawn import registry


def test_events_error_type_standardized(tmp_path, monkeypatch):
    """Verify events use 'error' not 'error_occurred'."""
    space_dir = tmp_path / ".space"
    space_dir.mkdir()

    monkeypatch.setattr(paths, "space_root", lambda: space_dir)
    monkeypatch.setattr("space.events.DB_PATH", space_dir / "events.db")

    # Directly emit error via events module
    events.emit("test", "error", None, "test error message")

    db_path = space_dir / "events.db"
    with sqlite3.connect(db_path) as conn:
        # Check no old-style errors
        old_style = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'error_occurred'"
        ).fetchone()[0]

        # Check new-style errors exist
        new_style = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'error'"
        ).fetchone()[0]

        assert old_style == 0, "Found old-style 'error_occurred' events"
        assert new_style >= 1, "No 'error' events found"


def test_errors_command_displays_logged_errors(tmp_path, monkeypatch):
    """space errors command queries and displays errors."""
    space_dir = tmp_path / ".space"
    space_dir.mkdir()

    monkeypatch.setattr(paths, "space_root", lambda: space_dir)
    monkeypatch.setattr("space.events.DB_PATH", space_dir / "events.db")
    registry.init_db()

    # Log some errors
    agent_id = registry.ensure_agent("test-agent")
    events.emit("bridge", "error", agent_id, "test error 1")
    events.emit("memory", "error", agent_id, "test error 2")

    runner = CliRunner()
    result = runner.invoke(space_app, ["errors", "--limit", "10"])

    assert result.exit_code == 0
    assert "Last 2 errors" in result.stdout
    assert "test error" in result.stdout
