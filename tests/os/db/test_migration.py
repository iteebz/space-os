import pytest
import sqlite3
from unittest.mock import patch
from pathlib import Path
import sys

from space.os.db.migration import init_migrations_table, get_applied_migrations, get_available_migrations, Migration, apply_migrations

# --- Constants for Mock Migration Content ---
INIT_MIGRATION_CONTENT = """
def upgrade(cursor):
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
def downgrade(cursor):
    cursor.execute("DROP TABLE users")
"""

ADD_SETTINGS_MIGRATION_CONTENT = """
def upgrade(cursor):
    cursor.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
def downgrade(cursor):
    cursor.execute("DROP TABLE settings")
"""

ADD_EMAIL_MIGRATION_CONTENT = """
def upgrade(cursor):
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
def downgrade(cursor):
    cursor.execute("ALTER TABLE users DROP COLUMN email")
"""

# --- Helper for writing mock migration files ---
def _write_migration_file(app_dir: Path, version: str, content: str):
    (app_dir / f"{version}.py").write_text(content)

# --- Fixtures ---
@pytest.fixture
def mock_db_connection():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def mock_migrations_dir(tmp_path):
    migrations_root = tmp_path / "os" / "db" / "migrations"
    app_migrations_dir = migrations_root / "test_app"
    app_migrations_dir.mkdir(parents=True)

    _write_migration_file(app_migrations_dir, "V20231027000000_init", INIT_MIGRATION_CONTENT)
    _write_migration_file(app_migrations_dir, "V20231027003000_add_settings", ADD_SETTINGS_MIGRATION_CONTENT)
    _write_migration_file(app_migrations_dir, "V20231027010000_add_email_to_users", ADD_EMAIL_MIGRATION_CONTENT)
    (app_migrations_dir / "not_a_migration.txt").touch()

    sys.path.insert(0, str(migrations_root.parent.parent))
    yield migrations_root
    sys.path.remove(str(migrations_root.parent.parent))

# --- Tests for init_migrations_table ---
def test_init_migrations_table_creates_table(mock_db_connection):
    cursor = mock_db_connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations';")
    assert cursor.fetchone() is None
    init_migrations_table(mock_db_connection)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations';")
    assert cursor.fetchone() == ('_migrations',)

def test_init_migrations_table_does_nothing_if_table_exists(mock_db_connection):
    cursor = mock_db_connection.cursor()
    cursor.execute("CREATE TABLE _migrations (version TEXT PRIMARY KEY, applied_at TEXT)")
    cursor.execute("INSERT INTO _migrations (version, applied_at) VALUES ('v1', 'now')")
    mock_db_connection.commit()
    init_migrations_table(mock_db_connection)
    cursor.execute("SELECT version FROM _migrations")
    assert cursor.fetchone() == ('v1',)

# --- Tests for get_applied_migrations ---
def test_get_applied_migrations_returns_correct_set(mock_db_connection):
    init_migrations_table(mock_db_connection)
    cursor = mock_db_connection.cursor()
    cursor.execute("INSERT INTO _migrations (version) VALUES ('V1'), ('V2')")
    mock_db_connection.commit()
    applied = get_applied_migrations(mock_db_connection)
    assert applied == {'V1', 'V2'}

def test_get_applied_migrations_returns_empty_set_if_none_applied(mock_db_connection):
    init_migrations_table(mock_db_connection)
    applied = get_applied_migrations(mock_db_connection)
    assert applied == set()

# --- Tests for get_available_migrations ---
def test_get_available_migrations_discovers_and_sorts_correctly(mock_migrations_dir):
    with patch("space.os.db.migration.MIGRATIONS_ROOT", mock_migrations_dir):
        available = get_available_migrations("test_app")
        expected = [
            "V20231027000000_init",
            "V20231027003000_add_settings",
            "V20231027010000_add_email_to_users",
        ]
        assert [m.version for m in available] == expected

def test_get_available_migrations_returns_empty_for_non_existent_app(mock_migrations_dir):
    with patch("space.os.db.migration.MIGRATIONS_ROOT", mock_migrations_dir):
        available = get_available_migrations("non_existent_app")
        assert available == []

def test_get_available_migrations_returns_empty_for_empty_dir(tmp_path):
    migrations_root = tmp_path / "os" / "db" / "migrations"
    (migrations_root / "empty_app").mkdir(parents=True)
    with patch("space.os.db.migration.MIGRATIONS_ROOT", migrations_root):
        available = get_available_migrations("empty_app")
        assert available == []

# --- Tests for apply_migrations ---
def test_apply_migrations_applies_all_pending(mock_db_connection, mock_migrations_dir):
    with patch("space.os.db.migration.MIGRATIONS_ROOT", mock_migrations_dir):
        apply_migrations("test_app", mock_db_connection)

        applied = get_applied_migrations(mock_db_connection)
        assert applied == {
            "V20231027000000_init",
            "V20231027003000_add_settings",
            "V20231027010000_add_email_to_users",
        }

        cursor = mock_db_connection.cursor()
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [col[1] for col in cursor.fetchall()]
        assert "id" in user_cols
        assert "name" in user_cols
        assert "email" in user_cols

        cursor.execute("PRAGMA table_info(settings)")
        setting_cols = [col[1] for col in cursor.fetchall()]
        assert "key" in setting_cols
        assert "value" in setting_cols

def test_apply_migrations_skips_already_applied(mock_db_connection, mock_migrations_dir):
    with patch("space.os.db.migration.MIGRATIONS_ROOT", mock_migrations_dir):
        # Manually apply the first migration and record it
        init_migrations_table(mock_db_connection)
        cursor = mock_db_connection.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO _migrations (version) VALUES ('V20231027000000_init')")
        mock_db_connection.commit()

        apply_migrations("test_app", mock_db_connection)

        applied = get_applied_migrations(mock_db_connection)
        assert applied == {
            "V20231027000000_init",
            "V20231027003000_add_settings",
            "V20231027010000_add_email_to_users",
        }

        cursor = mock_db_connection.cursor()
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [col[1] for col in cursor.fetchall()]
        assert "id" in user_cols
        assert "name" in user_cols
        assert "email" in user_cols

        cursor.execute("PRAGMA table_info(settings)")
        setting_cols = [col[1] for col in cursor.fetchall()]
        assert "key" in setting_cols
        assert "value" in setting_cols
