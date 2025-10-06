import pytest
import sqlite3
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Assuming migration_manager.py will be in space/os/db/
from space.os.db.migration_manager import init_migrations_table, get_applied_migrations, get_available_migrations, MIGRATIONS_ROOT, Migration

@pytest.fixture
def mock_db_connection():
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def mock_migrations_dir(tmp_path):
    # Create a mock migrations directory structure
    migrations_root = tmp_path / "os" / "db" / "migrations"
    app_migrations_dir = migrations_root / "test_app"
    app_migrations_dir.mkdir(parents=True)

    # Create some mock migration files
    # V20231027000000_init.py
    with open(app_migrations_dir / "V20231027000000_init.py", "w") as f:
        f.write("""
def upgrade(cursor):
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
def downgrade(cursor):
    cursor.execute("DROP TABLE users")
""")

    # V20231027003000_add_settings.py
    with open(app_migrations_dir / "V20231027003000_add_settings.py", "w") as f:
        f.write("""
def upgrade(cursor):
    cursor.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
def downgrade(cursor):
    cursor.execute("DROP TABLE settings")
""")

    # V20231027010000_add_email_to_users.py
    with open(app_migrations_dir / "V20231027010000_add_email_to_users.py", "w") as f:
        f.write("""
def upgrade(cursor):
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
def downgrade(cursor):
    cursor.execute("ALTER TABLE users DROP COLUMN email")
""")

    # Not a migration file
    (app_migrations_dir / "not_a_migration.txt").touch()

    # Add the mock migrations root to sys.path for module loading
    sys.path.insert(0, str(migrations_root.parent.parent))
    yield migrations_root
    sys.path.remove(str(migrations_root.parent.parent))

def test_init_migrations_table_creates_table(mock_db_connection):
    """
    Test that init_migrations_table creates the _migrations table if it doesn't exist.
    """
    cursor = mock_db_connection.cursor()
    # Verify table does not exist initially
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations';")
    assert cursor.fetchone() is None

    init_migrations_table(mock_db_connection)

    # Verify table now exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations';")
    assert cursor.fetchone() == ('_migrations',)

def test_init_migrations_table_does_nothing_if_table_exists(mock_db_connection):
    """
    Test that init_migrations_table does not alter the table if it already exists.
    """
    cursor = mock_db_connection.cursor()
    cursor.execute("CREATE TABLE _migrations (version TEXT PRIMARY KEY, applied_at TEXT)")
    cursor.execute("INSERT INTO _migrations (version, applied_at) VALUES ('v1', 'now')")
    mock_db_connection.commit()

    init_migrations_table(mock_db_connection)

    cursor.execute("SELECT version FROM _migrations")
    assert cursor.fetchone() == ('v1',)

def test_get_applied_migrations_returns_correct_set(mock_db_connection):
    """
    Test that get_applied_migrations returns the set of applied migration versions.
    """
    init_migrations_table(mock_db_connection)
    cursor = mock_db_connection.cursor()
    cursor.execute("INSERT INTO _migrations (version) VALUES ('V1'), ('V2')")
    mock_db_connection.commit()

    applied = get_applied_migrations(mock_db_connection)
    assert applied == {'V1', 'V2'}

def test_get_applied_migrations_returns_empty_set_if_none_applied(mock_db_connection):
    """
    Test that get_applied_migrations returns an empty set if no migrations have been applied.
    """
    init_migrations_table(mock_db_connection)
    applied = get_applied_migrations(mock_db_connection)
    assert applied == set()

def test_get_available_migrations_discovers_and_sorts_correctly(mock_migrations_dir):
    """
    Test that get_available_migrations discovers and sorts migration files correctly.
    """
    with patch("space.os.db.migration_manager.MIGRATIONS_ROOT", mock_migrations_dir):
        available = get_available_migrations("test_app")
        expected = [
            "V20231027000000_init",
            "V20231027003000_add_settings",
            "V20231027010000_add_email_to_users",
        ]
        assert [m.version for m in available] == expected

def test_get_available_migrations_returns_empty_for_non_existent_app(mock_migrations_dir):
    """
    Test that get_available_migrations returns an empty list for a non-existent app.
    """
    with patch("space.os.db.migration_manager.MIGRATIONS_ROOT", mock_migrations_dir):
        available = get_available_migrations("non_existent_app")
        assert available == []

def test_get_available_migrations_returns_empty_for_empty_dir(tmp_path):
    """
    Test that get_available_migrations returns an empty list for an empty app migrations directory.
    """
    migrations_root = tmp_path / "os" / "db" / "migrations"
    (migrations_root / "empty_app").mkdir(parents=True)
    with patch("space.os.db.migration_manager.MIGRATIONS_ROOT", migrations_root):
        available = get_available_migrations("empty_app")
        assert available == []

def test_apply_migrations_applies_all_pending(mock_db_connection, mock_migrations_dir):
    """
    Test that apply_migrations applies all pending migrations in order.
    """
    with patch("space.os.db.migration_manager.MIGRATIONS_ROOT", mock_migrations_dir):
        from space.os.db.migration_manager import apply_migrations
        apply_migrations("test_app", mock_db_connection)

        # Verify all migrations are applied
        applied = get_applied_migrations(mock_db_connection)
        assert applied == {
            "V20231027000000_init",
            "V20231027003000_add_settings",
            "V20231027010000_add_email_to_users",
        }

        # Verify schema changes
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
    """
    Test that apply_migrations skips migrations that are already applied.
    """
    with patch("space.os.db.migration_manager.MIGRATIONS_ROOT", mock_migrations_dir):
        from space.os.db.migration_manager import apply_migrations

        # Manually apply the first migration and record it
        init_migrations_table(mock_db_connection)
        cursor = mock_db_connection.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO _migrations (version) VALUES ('V20231027000000_init')")
        mock_db_connection.commit()

        # Call apply_migrations - it should only apply the remaining ones
        apply_migrations("test_app", mock_db_connection)

        # Verify all migrations are now recorded as applied
        applied = get_applied_migrations(mock_db_connection)
        assert applied == {
            "V20231027000000_init",
            "V20231027003000_add_settings",
            "V20231027010000_add_email_to_users",
        }

        # Verify schema changes from all migrations (including the manually applied one)
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