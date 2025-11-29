"""Trace CLI tests."""

from unittest.mock import patch

from typer.testing import CliRunner

from space.os.spawn.cli import app

runner = CliRunner()


def test_trace_agent_identity():
    """Trace command with agent identity shows recent spawns."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.return_value = {
            "type": "identity",
            "identity": "zealot",
            "agent_id": "agent-123",
            "recent_spawns": [
                {
                    "session_id": "7a6a07de-1234-5678-90ab-cdef12345678",
                    "short_id": "7a6a07de",
                    "status": "COMPLETED",
                    "started_at": "2025-11-03T10:00:00",
                    "duration_seconds": 5.2,
                    "outcome": "Task completed successfully",
                },
                {
                    "session_id": "9b7b18ef-1234-5678-90ab-cdef12345678",
                    "short_id": "9b7b18ef",
                    "status": "FAILED",
                    "started_at": "2025-11-03T09:55:00",
                    "duration_seconds": 2.1,
                    "outcome": "ERROR: Connection timeout",
                },
            ],
        }

        result = runner.invoke(app, ["trace", "zealot"])

    assert result.exit_code == 0
    assert "zealot" in result.stdout
    assert "7a6a07de" in result.stdout
    assert "COMPLETED" in result.stdout or "✓" in result.stdout
    mock_trace.assert_called_once_with("zealot")


def test_trace_session_id():
    """Trace command with session ID shows full context."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.return_value = {
            "type": "session",
            "session_id": "7a6a07de-1234-5678-90ab-cdef12345678",
            "short_id": "7a6a07de",
            "identity": "zealot",
            "status": "COMPLETED",
            "started_at": "2025-11-03T10:00:00",
            "ended_at": "2025-11-03T10:00:05",
            "duration_seconds": 5.2,
            "triggered_by": "bridge:#general",
            "channel_id": "channel-123",
            "channel_context": {
                "content": "Can you analyze this code?",
                "from_agent": "admin",
                "at": "2025-11-03T09:59:50",
            },
            "input": "Analyze the provided code snippet for security issues",
            "output": "The code has potential SQL injection vulnerabilities...",
            "stderr": None,
            "last_memory_mutation": {
                "message": "Found 3 security issues in analyzed code",
                "topic": "security",
                "at": "2025-11-03T10:00:04",
            },
        }

        result = runner.invoke(app, ["trace", "7a6a07de"])

    assert result.exit_code == 0
    assert "7a6a07de" in result.stdout
    assert "zealot" in result.stdout
    assert "COMPLETED" in result.stdout or "✓" in result.stdout
    assert "Input" in result.stdout
    assert "Output" in result.stdout
    assert "Memory" in result.stdout
    mock_trace.assert_called_once_with("7a6a07de")


def test_trace_channel_id():
    """Trace command with channel ID shows participants."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.return_value = {
            "type": "channel",
            "channel_id": "channel-123",
            "channel_name": "general",
            "participants": [
                {
                    "agent_id": "agent-1",
                    "identity": "zealot",
                    "last_message_at": "2025-11-03T10:05:00",
                    "last_message": "Task analysis complete, summary follows",
                },
                {
                    "agent_id": "agent-2",
                    "identity": "scribe",
                    "last_message_at": "2025-11-03T10:04:30",
                    "last_message": "Recording findings in memory",
                },
            ],
        }

        result = runner.invoke(app, ["trace", "general"])

    assert result.exit_code == 0
    assert "general" in result.stdout
    assert "zealot" in result.stdout
    assert "scribe" in result.stdout
    mock_trace.assert_called_once_with("general")


def test_trace_no_args_shows_help():
    """Trace command with no arguments shows help."""
    result = runner.invoke(app, ["trace"])

    assert result.exit_code == 0
    assert "Trace execution" in result.stdout or "Usage" in result.stdout


def test_trace_invalid_query_error():
    """Trace command with invalid query shows error."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.side_effect = ValueError("Query 'invalid-query' not found")

        result = runner.invoke(app, ["trace", "invalid-query"])

    assert result.exit_code == 1
    assert "not found" in result.stdout or "not found" in result.stderr


def test_trace_agent_no_spawns():
    """Trace for agent with no spawns shows appropriate message."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.return_value = {
            "type": "identity",
            "identity": "new-agent",
            "agent_id": "agent-999",
            "recent_spawns": [],
        }

        result = runner.invoke(app, ["trace", "new-agent"])

    assert result.exit_code == 0
    assert "No spawns found" in result.stdout


def test_trace_channel_no_activity():
    """Trace for channel with no activity shows appropriate message."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.return_value = {
            "type": "channel",
            "channel_id": "channel-999",
            "channel_name": "empty",
            "participants": [],
        }

        result = runner.invoke(app, ["trace", "empty"])

    assert result.exit_code == 0
    assert "No activity" in result.stdout


def test_trace_session_with_error():
    """Trace for failed session shows error details."""
    with patch("space.os.spawn.trace.trace_query") as mock_trace:
        mock_trace.return_value = {
            "type": "session",
            "session_id": "failed-session-id",
            "short_id": "failed",
            "identity": "zealot",
            "status": "FAILED",
            "started_at": "2025-11-03T10:00:00",
            "ended_at": "2025-11-03T10:00:02",
            "duration_seconds": 2.0,
            "triggered_by": "bridge:#general",
            "channel_id": "channel-123",
            "channel_context": None,
            "input": "Perform analysis",
            "output": None,
            "stderr": "Connection refused: unable to reach service",
            "last_memory_mutation": None,
        }

        result = runner.invoke(app, ["trace", "failed-session-id"])

    assert result.exit_code == 0
    assert "failed" in result.stdout.lower() or "✗" in result.stdout
    assert "Error" in result.stdout
    assert "Connection refused" in result.stdout


def test_trace_spawn_syncs_session():
    """Trace spawn should sync session to get latest data."""
    from unittest.mock import MagicMock

    with patch("space.os.spawn.spawns.get_spawn") as mock_get_spawn:
        with patch("space.lib.uuid7.resolve_id") as mock_resolve_id:
            with patch("space.os.sessions.sync.ingest") as mock_sync:
                mock_resolve_id.return_value = "abc12345-def6-7890-ghij-klmnopqrstuv"

                spawn_obj = MagicMock()
                spawn_obj.id = "abc12345-def6-7890-ghij-klmnopqrstuv"
                spawn_obj.session_id = "sess-123"
                spawn_obj.agent_id = "agent-456"
                spawn_obj.status = "completed"
                spawn_obj.created_at = "2025-11-03T10:00:00"
                spawn_obj.ended_at = "2025-11-03T10:00:05"
                spawn_obj.channel_id = None

                mock_get_spawn.return_value = spawn_obj

                with patch("space.os.spawn.agents.get_agent") as mock_get_agent:
                    agent_obj = MagicMock()
                    agent_obj.identity = "zealot"
                    mock_get_agent.return_value = agent_obj

                    from space.os.spawn.trace import trace_spawn

                    result = trace_spawn("abc12345")

                    mock_sync.assert_called_once_with("sess-123")
                    assert result["spawn_id"] == "abc12345"
                    assert result["session_id"] == "sess-123"
