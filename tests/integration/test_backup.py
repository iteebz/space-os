import os
from pathlib import Path

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_backup(monkeypatch, tmp_path):
    temp_space_dir = tmp_path / ".space"
    temp_space_dir.mkdir(exist_ok=True)

    (temp_space_dir / "file1.db").write_text("content1")
    (temp_space_dir / "subdir").mkdir(exist_ok=True)
    (temp_space_dir / "subdir" / "file2.db").write_text("content2")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os.path, "expanduser", lambda path: path.replace("~", str(tmp_path)))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home_dir")

    result = runner.invoke(app, ["backup"])
    assert result.exit_code == 0
    assert "Backed up to" in result.stdout

    backup_base_dir = tmp_path / "home_dir" / ".space" / "backups"
    backup_dirs = sorted([d for d in backup_base_dir.iterdir() if d.is_dir()], reverse=True)
    assert len(backup_dirs) > 0

    latest_backup_dir = backup_dirs[0]
    assert (latest_backup_dir / "file1.db").read_text() == "content1"
    assert (latest_backup_dir / "subdir" / "file2.db").read_text() == "content2"
    assert not (latest_backup_dir / ".space" / "subdir" / "file2.db").is_symlink()
