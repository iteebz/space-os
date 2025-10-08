import os
from pathlib import Path

from typer.testing import CliRunner

from space.bridge.cli import app as bridge_app
from space.cli import app as space_app
from space.knowledge.cli import app as knowledge_app
from space.memory.cli import app as memory_app
from space.spawn.cli import app as spawn_app

runner = CliRunner()


def test_space_smoketest():
    result = runner.invoke(space_app)
    assert "WELCOME TO AGENT-SPACE" in result.stdout


def test_bridge_smoketest():
    result = runner.invoke(bridge_app)

    assert (
        "IDENTITY SYSTEM:" in result.stdout or "IDENTITY SYSTEM:" in result.stderr
    )  # Check for a known instruction from bridge.cli


def test_spawn_smoketest():
    result = runner.invoke(spawn_app)

    assert (
        "Constitutional agent registry" in result.stdout
        or "Constitutional agent registry" in result.stderr
    )  # Check for a known instruction from spawn.cli


def test_space_agents_smoketest():
    result = runner.invoke(space_app, ["agents"])

    assert result.exit_code == 0

    assert "codelot" in result.stdout  # Check for a known agent ID


def test_memory_smoketest():
    result = runner.invoke(memory_app)

    assert (
        "MEMORY PROTOCOL:" in result.stdout or "MEMORY PROTOCOL:" in result.stderr
    )  # Check for a known instruction from memory.cli


def test_knowledge_smoketest():
    result = runner.invoke(knowledge_app)

    assert (
        "ID         DOMAIN          CONTRIBUTOR     CREATED             " in result.stdout
        or "ID         DOMAIN          CONTRIBUTOR     CREATED             " in result.stderr
    )  # Check for a known instruction from knowledge.cli


def test_space_backup_creates_backup_directory_and_copies_files(monkeypatch, tmp_path):
    # Setup a temporary .space directory for the test

    temp_space_dir = tmp_path / ".space"

    temp_space_dir.mkdir(exist_ok=True)

    # Create dummy files in the temporary .space directory

    (temp_space_dir / "file1.db").write_text("content1")

    (temp_space_dir / "subdir").mkdir(exist_ok=True)

    (temp_space_dir / "subdir" / "file2.db").write_text("content2")

    # Mock the root() function to point to tmp_path

    from space.lib import db_utils

    monkeypatch.setattr(db_utils, "root", lambda: tmp_path)

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
