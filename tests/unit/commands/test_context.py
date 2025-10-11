from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from space.cli import app
from space.commands import context

runner = CliRunner()


@patch("space.commands.context.datetime")
@patch("space.commands.context._collect_timeline")
@patch("space.commands.context._collect_current_state")
@patch("space.commands.context._search_lattice")
def test_context_output(
    mock_search_lattice, mock_collect_current_state, mock_collect_timeline, mock_datetime
):
    mock_datetime.fromtimestamp.return_value.strftime.return_value = "2023-03-15 13:20"
    mock_collect_timeline.return_value = [
        {
            "timestamp": 1678886400,
            "source": "events",
            "type": "test.event",
            "identity": "test-agent",
            "data": "Test event data",
        }
    ]
    mock_collect_current_state.return_value = {
        "memory": [
            {
                "identity": "test-agent",
                "topic": "test-topic",
                "message": "Test memory message",
            }
        ],
        "knowledge": [],
        "bridge": [],
    }
    mock_search_lattice.return_value = {"Test Heading": "Test lattice content"}

    result = runner.invoke(app, ["context", "test-topic"])

    assert result.exit_code == 0
    assert "## EVOLUTION (last 10)" in result.stdout
    assert "[2023-03-15 13:20] test.event (test-agent)" in result.stdout
    assert "## CURRENT STATE" in result.stdout
    assert "memory: 1" in result.stdout
    assert "## LATTICE DOCS" in result.stdout
    assert "### Test Heading" in result.stdout


@patch("space.commands.context.libdb.connect")
@patch("space.commands.context.memory_db.connect")
@patch("space.commands.context.knowledge_db.database_path")
@patch("space.commands.context.bridge_config.DB_PATH")
@patch("space.events.DB_PATH")
@patch("space.commands.context.memory_db.database_path")
def test_collect_timeline(
    mock_memory_db_path,
    mock_events_db_path,
    mock_bridge_db_path,
    mock_knowledge_db_path,
    mock_memory_db_connect,
    mock_libdb_connect,
):
    # Setup mocks
    mock_events_db_path.exists.return_value = True
    mock_memory_db_path.return_value.exists.return_value = True
    mock_knowledge_db_path.return_value.exists.return_value = False
    mock_bridge_db_path.exists.return_value = False

    mock_libdb_connection = MagicMock()
    mock_libdb_cursor = MagicMock()
    mock_libdb_cursor.fetchall.return_value = [
        (1, "events", "test-agent", "test.event", "Test event data", 1678886400)
    ]
    mock_libdb_connection.execute.return_value = mock_libdb_cursor
    mock_libdb_connect.return_value.__enter__.return_value = mock_libdb_connection

    mock_mem_connection = MagicMock()
    mock_mem_cursor = MagicMock()
    mock_mem_cursor.description = [("identity",), ("topic",), ("message",), ("created_at",)]
    mock_mem_cursor.fetchall.return_value = [
        ("test-agent", "test-topic", "test message", 1678886401)
    ]
    mock_mem_connection.execute.return_value = mock_mem_cursor
    mock_memory_db_connect.return_value.__enter__.return_value = mock_mem_connection

    # Call the function
    timeline = context._collect_timeline("test", None, False)

    # Assertions
    assert len(timeline) == 2
    assert timeline[0]["source"] == "events"
    assert timeline[1]["source"] == "memory"
