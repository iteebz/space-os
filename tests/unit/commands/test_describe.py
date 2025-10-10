from unittest.mock import patch

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


@patch("space.commands.describe.registry.init_db")
@patch("space.commands.describe.registry.set_self_description")
def test_set_description(mock_set, mock_init):
    mock_set.return_value = True
    result = runner.invoke(app, ["describe", "--as", "test-agent", "test description"])
    assert result.exit_code == 0
    assert "test-agent: test description" in result.stdout
    mock_set.assert_called_once_with("test-agent", "test description")


@patch("space.commands.describe.registry.init_db")
@patch("space.commands.describe.registry.get_self_description")
def test_get_description(mock_get, mock_init):
    mock_get.return_value = "existing description"
    result = runner.invoke(app, ["describe", "--as", "test-agent"])
    assert result.exit_code == 0
    assert "existing description" in result.stdout
    mock_get.assert_called_once_with("test-agent")


@patch("space.commands.describe.registry.init_db")
@patch("space.commands.describe.registry.get_self_description")
def test_get_missing_description(mock_get, mock_init):
    mock_get.return_value = None
    result = runner.invoke(app, ["describe", "--as", "test-agent"])
    assert result.exit_code == 0
    assert "No self-description for test-agent" in result.stdout
