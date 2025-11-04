import sqlite3
from unittest.mock import patch

from space.lib.backup import _get_backup_stats, backup


@patch("space.lib.backup.paths.backup_sessions_dir")
@patch("space.lib.backup.paths.backup_snapshot")
@patch("space.lib.backup.paths.sessions_dir")
@patch("space.lib.backup.paths.space_data")
def test_backup_creates_timestamped_data_dir(
    mock_space_data, mock_sessions_dir, mock_backup_snapshot, mock_backup_sessions_dir, tmp_path
):
    """Backup creates timestamped data directory."""
    src_data = tmp_path / "data"
    src_data.mkdir()
    (src_data / "test.db").write_text("")

    src_sessions = tmp_path / "sessions"
    src_sessions.mkdir()

    backup_dir = tmp_path / "backups"

    mock_space_data.return_value = src_data
    mock_sessions_dir.return_value = src_sessions
    mock_backup_snapshot.side_effect = lambda ts: backup_dir / "data" / ts
    mock_backup_sessions_dir.return_value = backup_dir / "sessions"

    backup(quiet_output=True)

    assert (backup_dir / "data").exists()
    data_backups = list((backup_dir / "data").glob("*"))
    assert len(data_backups) == 1
    assert data_backups[0].is_dir()
    assert (backup_dir / "sessions").exists()


@patch("space.lib.backup.paths.backup_sessions_dir")
@patch("space.lib.backup.paths.backup_snapshot")
@patch("space.lib.backup.paths.sessions_dir")
@patch("space.lib.backup.paths.space_data")
def test_backup_copies_db_files(
    mock_space_data, mock_sessions_dir, mock_backup_snapshot, mock_backup_sessions_dir, tmp_path
):
    """Backup copies all .db files to data snapshot."""
    src_data = tmp_path / "data"
    src_data.mkdir()

    conn = sqlite3.connect(src_data / "test.db")
    conn.execute("CREATE TABLE data (id INTEGER)")
    conn.execute("INSERT INTO data VALUES (1)")
    conn.commit()
    conn.close()

    src_sessions = tmp_path / "sessions"
    src_sessions.mkdir()

    backup_dir = tmp_path / "backups"

    mock_space_data.return_value = src_data
    mock_sessions_dir.return_value = src_sessions
    mock_backup_snapshot.side_effect = lambda ts: backup_dir / "data" / ts
    mock_backup_sessions_dir.return_value = backup_dir / "sessions"

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


@patch("space.lib.backup.paths.backup_sessions_dir")
@patch("space.lib.backup.paths.sessions_dir")
def test_backup_sessions_mirror_structure(mock_sessions_dir, mock_backup_sessions_dir, tmp_path):
    """Session backup mirrors structure and is additive (overwrites updated files, preserves backup-only files)."""
    from space.lib.backup import _backup_sessions

    src_sessions = tmp_path / "sessions"
    src_sessions.mkdir()
    (src_sessions / "claude").mkdir()
    (src_sessions / "codex").mkdir()

    backup_dir = tmp_path / "backup"

    mock_sessions_dir.return_value = src_sessions
    mock_backup_sessions_dir.return_value = backup_dir

    (src_sessions / "claude" / "session1.jsonl").write_text("msg1")
    (src_sessions / "codex" / "session2.jsonl").write_text("msg2")

    _backup_sessions(quiet_output=True)

    assert (backup_dir / "claude" / "session1.jsonl").read_text() == "msg1"
    assert (backup_dir / "codex" / "session2.jsonl").read_text() == "msg2"

    (src_sessions / "claude" / "session3.jsonl").write_text("msg3")
    (src_sessions / "claude" / "session1.jsonl").write_text("msg1-updated")

    _backup_sessions(quiet_output=True)

    assert (backup_dir / "claude" / "session1.jsonl").read_text() == "msg1-updated"
    assert (backup_dir / "claude" / "session3.jsonl").read_text() == "msg3"
    assert (backup_dir / "codex" / "session2.jsonl").read_text() == "msg2"
