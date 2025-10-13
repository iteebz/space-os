from pathlib import Path

from typer.testing import CliRunner

from space.bridge.cli import app as bridge_app
from space.cli import app as space_app
from space.memory.cli import app as memory_app

runner = CliRunner()


def test_space():
    result = runner.invoke(space_app)
    readme = (Path(__file__).parent.parent.parent / "space" / "README.md").read_text()
    assert result.stdout == readme


def test_bridge():
    result = runner.invoke(bridge_app)
    readme = (Path(__file__).parent.parent.parent / "space" / "bridge" / "README.md").read_text()
    assert readme in result.stdout


def test_memory():
    result = runner.invoke(memory_app)
    readme = (Path(__file__).parent.parent.parent / "space" / "memory" / "README.md").read_text()
    assert result.stdout == readme
