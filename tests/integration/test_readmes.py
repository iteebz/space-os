from typer.testing import CliRunner

from space.bridge.app import app as bridge_app
from space.cli import app as space_app
from space.memory.app import app as memory_app

runner = CliRunner()


def test_space():
    result = runner.invoke(space_app)
    assert "Space CLI - A command-line interface for Space." in result.stdout


def test_bridge():
    result = runner.invoke(bridge_app)
    assert "Bridge CLI - A command-line interface for Bridge." in result.stdout


def test_memory():
    result = runner.invoke(memory_app)
    assert "Memory CLI - A command-line interface for Memory." in result.stdout
