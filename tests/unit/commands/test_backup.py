import sqlite3
from unittest.mock import patch

from space.commands.backup import _get_backup_stats, backup


def test_backup_creates_timestamped_dir(tmp_path):
    """Backup creates timestamped directory."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.db").write_text("")

    backup_dir = tmp_path / "backups"

    with patch("space.commands.backup.paths.dot_space", return_value=src_dir):
        with patch("space.commands.backup.paths.backups_dir", return_value=backup_dir):
            backup(quiet_output=True)

    assert backup_dir.exists()
    backups = list(backup_dir.glob("*"))
    assert len(backups) == 1
    assert backups[0].is_dir()


def test_backup_copies_db_files(tmp_path):
    """Backup copies all .db files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    conn = sqlite3.connect(src_dir / "test.db")
    conn.execute("CREATE TABLE data (id INTEGER)")
    conn.execute("INSERT INTO data VALUES (1)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"

    with patch("space.commands.backup.paths.dot_space", return_value=src_dir):
        with patch("space.commands.backup.paths.backups_dir", return_value=backup_dir):
            backup(quiet_output=True)

    backups = list(backup_dir.glob("*"))
    backup_db = backups[0] / "test.db"
    assert backup_db.exists()


def test_backup_stats_counts_rows(tmp_path):
    """Backup stats accurately count rows."""
    backup_path = tmp_path / "backup"
    backup_path.mkdir()

    conn = sqlite3.connect(backup_path / "test.db")
    conn.execute("CREATE TABLE data (id INTEGER)")
    conn.execute("INSERT INTO data VALUES (1), (2), (3)")
    conn.commit()
    conn.close()

    stats = _get_backup_stats(backup_path)

    assert "test.db" in stats
    assert stats["test.db"]["rows"] == 3
    assert stats["test.db"]["tables"] == 1
