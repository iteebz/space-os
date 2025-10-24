import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from space.commands.backup import _get_backup_stats, _replay_and_clean, backup


def test_backup_creates_timestamped_dir(tmp_path):
    """Backup creates timestamped directory."""
    dot_space = tmp_path / "dot_space"
    dot_space.mkdir()
    (dot_space / "test.db").write_text("")
    
    backups_dir = tmp_path / "backups"
    
    with patch("space.commands.backup.paths.dot_space", return_value=dot_space):
        with patch("space.commands.backup.paths.global_root", return_value=tmp_path):
            backup(quiet_output=True)
    
    assert backups_dir.exists()
    backups = list(backups_dir.glob("*"))
    assert len(backups) == 1
    assert backups[0].is_dir()


def test_backup_copies_db_files(tmp_path):
    """Backup copies all .db files."""
    dot_space = tmp_path / "dot_space"
    dot_space.mkdir()
    
    conn = sqlite3.connect(dot_space / "test.db")
    conn.execute("CREATE TABLE data (id INTEGER)")
    conn.execute("INSERT INTO data VALUES (1)")
    conn.commit()
    conn.close()
    
    with patch("space.commands.backup.paths.dot_space", return_value=dot_space):
        with patch("space.commands.backup.paths.global_root", return_value=tmp_path):
            backup(quiet_output=True)
    
    backups = list((tmp_path / "backups").glob("*"))
    backup_db = backups[0] / "test.db"
    assert backup_db.exists()


def test_cleanup_removes_wal_shm(tmp_path):
    """Replay and clean removes WAL and SHM files."""
    backup_path = tmp_path / "backup"
    backup_path.mkdir()
    
    conn = sqlite3.connect(backup_path / "test.db")
    conn.execute("CREATE TABLE data (id INTEGER)")
    conn.commit()
    conn.close()
    
    (backup_path / "test.db-wal").write_bytes(b"dummy")
    (backup_path / "test.db-shm").write_bytes(b"dummy")
    
    _replay_and_clean(backup_path)
    
    assert not (backup_path / "test.db-wal").exists()
    assert not (backup_path / "test.db-shm").exists()


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
