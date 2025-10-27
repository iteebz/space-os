import sqlite3
from unittest.mock import patch

from space.apps.backup import _get_backup_stats, backup


@patch("space.apps.backup.paths.backup_chats_latest")
@patch("space.apps.backup.paths.backup_snapshot")
@patch("space.apps.backup.paths.chats_dir")
@patch("space.apps.backup.paths.space_data")
def test_backup_creates_timestamped_data_dir(
    mock_space_data, mock_chats_dir, mock_backup_snapshot, mock_backup_chats_latest, tmp_path
):
    """Backup creates timestamped data directory."""
    src_data = tmp_path / "data"
    src_data.mkdir()
    (src_data / "test.db").write_text("")

    src_chats = tmp_path / "chats"
    src_chats.mkdir()

    backup_dir = tmp_path / "backups"

    mock_space_data.return_value = src_data
    mock_chats_dir.return_value = src_chats
    mock_backup_snapshot.side_effect = lambda ts: backup_dir / "data" / ts
    mock_backup_chats_latest.return_value = backup_dir / "chats" / "latest"

    backup(quiet_output=True)

    assert (backup_dir / "data").exists()
    data_backups = list((backup_dir / "data").glob("*"))
    assert len(data_backups) == 1
    assert data_backups[0].is_dir()
    assert (backup_dir / "chats" / "latest").exists()


@patch("space.apps.backup.paths.backup_chats_latest")
@patch("space.apps.backup.paths.backup_snapshot")
@patch("space.apps.backup.paths.chats_dir")
@patch("space.apps.backup.paths.space_data")
def test_backup_copies_db_files(
    mock_space_data, mock_chats_dir, mock_backup_snapshot, mock_backup_chats_latest, tmp_path
):
    """Backup copies all .db files to data snapshot."""
    src_data = tmp_path / "data"
    src_data.mkdir()

    conn = sqlite3.connect(src_data / "test.db")
    conn.execute("CREATE TABLE data (id INTEGER)")
    conn.execute("INSERT INTO data VALUES (1)")
    conn.commit()
    conn.close()

    src_chats = tmp_path / "chats"
    src_chats.mkdir()

    backup_dir = tmp_path / "backups"

    mock_space_data.return_value = src_data
    mock_chats_dir.return_value = src_chats
    mock_backup_snapshot.side_effect = lambda ts: backup_dir / "data" / ts
    mock_backup_chats_latest.return_value = backup_dir / "chats" / "latest"

    backup(quiet_output=True)

    data_backups = list((backup_dir / "data").glob("*"))
    backup_db = data_backups[0] / "test.db"
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
