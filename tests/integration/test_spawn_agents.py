from typer.testing import CliRunner

from space.app import app
from space.spawn import registry

runner = CliRunner()


def test_describe_get(test_space):
    result = runner.invoke(app, ["describe", "--as", "test-agent"])
    assert result.exit_code == 0
    assert "test-agent" in result.stdout


def test_describe_requires_identity(test_space):
    result = runner.invoke(app, ["describe"])
    assert result.exit_code != 0


def test_agent_registry_persists(test_space):
    runner.invoke(app, ["wake", "--as", "persist-agent"])
    agent_id = registry.get_agent_id("persist-agent")
    assert agent_id is not None
    assert isinstance(agent_id, str)
    assert len(agent_id) > 0
