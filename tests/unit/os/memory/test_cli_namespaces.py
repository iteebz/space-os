import pytest
import typer
from typer.testing import CliRunner

from space.os.memory.cli import create_namespace_command

runner = CliRunner()


@pytest.fixture
def setup_mocks(mocker):
    mocker.patch(
        "space.os.memory.ops.namespace.add_entry", return_value=mocker.Mock(uuid="test-uuid")
    )
    mocker.patch("space.os.memory.ops.namespace.list_entries", return_value=[])
    mocker.patch("space.os.memory.cli.format_memory_entries", return_value="formatted entries")
    return mocker


def test_journal_add_entry(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("journal")(create_namespace_command("journal", "journal"))

    result = runner.invoke(main_app, ["journal", "Test message"])
    assert result.exit_code == 0
    assert "Added journal entry: test-uuid" in result.stdout


def test_journal_list_entries(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("journal")(create_namespace_command("journal", "journal"))

    result = runner.invoke(main_app, ["journal"])
    assert result.exit_code == 0
    assert "formatted entries" in result.stdout


def test_journal_list_entries_all(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("journal")(create_namespace_command("journal", "journal"))

    result = runner.invoke(main_app, ["journal", "--all"])
    assert result.exit_code == 0
    assert "formatted entries" in result.stdout


def test_notes_add_entry(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("notes")(create_namespace_command("notes", "note"))

    result = runner.invoke(main_app, ["notes", "Test note"])
    assert result.exit_code == 0
    assert "Added notes entry: test-uuid" in result.stdout


def test_notes_list_entries(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("notes")(create_namespace_command("notes", "note"))

    result = runner.invoke(main_app, ["notes"])
    assert result.exit_code == 0
    assert "formatted entries" in result.stdout


def test_tasks_add_entry(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("tasks")(create_namespace_command("tasks", "task"))

    result = runner.invoke(main_app, ["tasks", "Test task"])
    assert result.exit_code == 0
    assert "Added tasks entry: test-uuid" in result.stdout


def test_tasks_list_entries(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("tasks")(create_namespace_command("tasks", "task"))

    result = runner.invoke(main_app, ["tasks"])
    assert result.exit_code == 0
    assert "formatted entries" in result.stdout


def test_beliefs_add_entry(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("beliefs")(create_namespace_command("beliefs", "belief"))

    result = runner.invoke(main_app, ["beliefs", "Test belief"])
    assert result.exit_code == 0
    assert "Added beliefs entry: test-uuid" in result.stdout


def test_beliefs_list_entries(setup_mocks):
    def callback(ctx: typer.Context):
        ctx.obj = {"identity": "test-agent-id"}

    main_app = typer.Typer()
    main_app.callback()(callback)
    main_app.command("beliefs")(create_namespace_command("beliefs", "belief"))

    result = runner.invoke(main_app, ["beliefs"])
    assert result.exit_code == 0
    assert "formatted entries" in result.stdout


def test_namespace_without_identity_fails(setup_mocks):
    main_app = typer.Typer()
    main_app.command("journal")(create_namespace_command("journal", "journal"))

    result = runner.invoke(main_app, ["journal", "Test message"])
    assert result.exit_code != 0

    result = runner.invoke(main_app, ["journal"])
    assert result.exit_code != 0
