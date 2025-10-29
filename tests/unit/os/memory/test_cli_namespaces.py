import pytest
import typer
from typer.testing import CliRunner

from space.os.memory.cli.namespace import create_namespace_cli  # Import create_namespace_cli
from space.os.memory.ops import namespace as ops_namespace

runner = CliRunner()

# Create a dummy main app to register the namespace cli as a subcommand
main_app = typer.Typer()
main_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
main_app.add_typer(create_namespace_cli("notes", "note"), name="notes")
main_app.add_typer(create_namespace_cli("tasks", "task"), name="tasks")
main_app.add_typer(create_namespace_cli("beliefs", "belief"), name="beliefs")


@pytest.fixture(autouse=True)
def mock_ops_namespace(mocker):
    mock_add_entry = mocker.patch("space.os.memory.ops.namespace.add_entry")
    mock_add_entry.return_value = mocker.Mock(uuid="test-uuid")
    mocker.patch("space.os.memory.ops.namespace.list_entries", return_value=[])
    mocker.patch(
        "space.os.memory.cli.namespace.format_memory_entries", return_value="formatted entries"
    )
    mocker.patch("space.os.spawn.get_agent", return_value=mocker.Mock(agent_id="test-agent-id"))
    # Set the identity in the main_app's context object
    main_app.obj = {"identity": "test-agent-id"}


def test_journal_add_entry(mocker):
    result = runner.invoke(
        main_app, ["journal", "add", "Test message"], obj={"identity": "test-agent-id"}
    )
    assert result.exit_code == 0
    ops_namespace.add_entry.assert_called_once_with(mocker.ANY, "journal", "Test message")
    assert "Added journal entry: test-uuid" in result.stdout


def test_journal_list_entries(mocker):
    result = runner.invoke(main_app, ["journal", "list"], obj={"identity": "test-agent-id"})
    assert result.exit_code == 0
    ops_namespace.list_entries.assert_called_once_with(mocker.ANY, "journal", show_all=False)
    assert "formatted entries" in result.stdout


def test_journal_list_entries_all(mocker):
    result = runner.invoke(
        main_app, ["journal", "list", "--all"], obj={"identity": "test-agent-id"}
    )
    assert result.exit_code == 0
    ops_namespace.list_entries.assert_called_once_with(mocker.ANY, "journal", show_all=True)
    assert "formatted entries" in result.stdout


def test_notes_add_entry(mocker):
    result = runner.invoke(
        main_app, ["notes", "add", "Test note"], obj={"identity": "test-agent-id"}
    )
    assert result.exit_code == 0
    ops_namespace.add_entry.assert_called_once_with(mocker.ANY, "notes", "Test note")
    assert "Added notes entry: test-uuid" in result.stdout


def test_notes_list_entries(mocker):
    result = runner.invoke(main_app, ["notes", "list"], obj={"identity": "test-agent-id"})
    ops_namespace.list_entries.assert_called_once_with(mocker.ANY, "notes", show_all=False)
    assert "formatted entries" in result.stdout


def test_tasks_add_entry(mocker):
    result = runner.invoke(
        main_app, ["tasks", "add", "Test task"], obj={"identity": "test-agent-id"}
    )
    assert result.exit_code == 0
    ops_namespace.add_entry.assert_called_once_with(mocker.ANY, "tasks", "Test task")
    assert "Added tasks entry: test-uuid" in result.stdout


def test_tasks_list_entries(mocker):
    result = runner.invoke(main_app, ["tasks", "list"], obj={"identity": "test-agent-id"})
    assert result.exit_code == 0
    assert "formatted entries" in result.stdout


def test_beliefs_add_entry(mocker):
    result = runner.invoke(
        main_app, ["beliefs", "add", "Test belief"], obj={"identity": "test-agent-id"}
    )
    assert result.exit_code == 0
    ops_namespace.add_entry.assert_called_once_with(mocker.ANY, "beliefs", "Test belief")
    assert "Added beliefs entry: test-uuid" in result.stdout


def test_beliefs_list_entries(mocker):
    result = runner.invoke(main_app, ["beliefs", "list"], obj={"identity": "test-agent-id"})
    assert result.exit_code == 0
    ops_namespace.list_entries.assert_called_once_with(mocker.ANY, "beliefs", show_all=False)
    ops_namespace.list_entries.assert_called_once_with(mocker.ANY, "beliefs", show_all=False)
    assert "formatted entries" in result.stdout


def test_namespace_add_without_identity_fails():
    temp_app = typer.Typer()
    temp_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
    result = runner.invoke(temp_app, ["journal", "add", "Test message"])
    assert result.exit_code != 0
    assert "Agent identity must be provided via --as option." in result.stderr


def test_namespace_list_without_identity_fails():
    temp_app = typer.Typer()
    temp_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
    result = runner.invoke(temp_app, ["journal", "list"])
    assert result.exit_code != 0
    assert "Agent identity must be provided via --as option." in result.stderr


# Test that archive, core, replace are not available as subcommands for namespaces
def test_journal_archive_not_available():
    temp_app = typer.Typer()
    temp_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
    result = runner.invoke(
        temp_app,
        ["journal", "archive", "some-uuid"],
    )
    assert result.exit_code != 0
    assert "No such command 'archive'" in result.stderr


def test_journal_core_not_available():
    temp_app = typer.Typer()
    temp_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
    result = runner.invoke(temp_app, ["journal", "core", "some-uuid"])
    assert result.exit_code != 0
    assert "No such command 'core'" in result.stderr


def test_journal_replace_not_available():
    temp_app = typer.Typer()
    temp_app.add_typer(create_namespace_cli("journal", "journal"), name="journal")
    result = runner.invoke(
        temp_app,
        ["journal", "replace", "some-uuid", "new message"],
    )
    assert result.exit_code != 0
    assert "No such command 'replace'" in result.stderr
