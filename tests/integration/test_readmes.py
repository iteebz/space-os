from typer.testing import CliRunner

from space.app import app as space_app
from space.bridge.app import app as bridge_app
from space.memory.app import app as memory_app

runner = CliRunner()


def test_space():
    result = runner.invoke(space_app)
    assert "Welcome to space-os" in result.stdout


def test_bridge():
    result = runner.invoke(bridge_app)
    assert "BRIDGE" in result.stdout


def test_memory():
    result = runner.invoke(memory_app)
    assert "Working context" in result.stdout
