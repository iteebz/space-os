import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from space.bridge.cli import app as bridge_app
from space.cli import app as space_app
from space.memory.cli import app as memory_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_db(test_space):
    pass


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


def test_backup(monkeypatch, tmp_path):
    # Setup a temporary .space directory for the test

    temp_space_dir = tmp_path / ".space"

    temp_space_dir.mkdir(exist_ok=True)

    # Create dummy files in the temporary .space directory

    (temp_space_dir / "file1.db").write_text("content1")

    (temp_space_dir / "subdir").mkdir(exist_ok=True)

    (temp_space_dir / "subdir" / "file2.db").write_text("content2")

    monkeypatch.chdir(tmp_path)

    # Mock Path.home() to point to tmp_path so backups go to tmp_path/.space/backups

    monkeypatch.setattr(os.path, "expanduser", lambda path: path.replace("~", str(tmp_path)))

    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home_dir")
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(space_app, ["backup"])
    assert result.exit_code == 0

    assert "Backed up to" in result.stdout

    # Verify backup directory structure and content

    backup_base_dir = tmp_path / "home_dir" / ".space" / "backups"

    # Find the most recent backup directory

    backup_dirs = sorted([d for d in backup_base_dir.iterdir() if d.is_dir()], reverse=True)

    assert len(backup_dirs) > 0, "No backup directory was created."

    latest_backup_dir = backup_dirs[0]

    assert (latest_backup_dir / "file1.db").read_text() == "content1"
    assert (latest_backup_dir / "subdir" / "file2.db").read_text() == "content2"
    assert not (
        latest_backup_dir / ".space" / "subdir" / "file2.db"
    ).is_symlink()  # Ensure it's a copy, not a symlink
