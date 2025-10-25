"""Unit tests for storage protocol contract."""

from unittest.mock import MagicMock

from space.core.protocols import Storage


def test_storage_protocol_connect():
    """Storage implements connect method."""
    storage = MagicMock(spec=Storage)
    storage.connect("path/to/db")
    storage.connect.assert_called_once_with("path/to/db")


def test_storage_protocol_ensure_schema():
    """Storage implements ensure_schema method."""
    storage = MagicMock(spec=Storage)
    storage.ensure_schema("path", "CREATE TABLE test (id TEXT)")
    storage.ensure_schema.assert_called_once()


def test_storage_protocol_ensure_schema_with_migrations():
    """Storage accepts migrations in ensure_schema."""
    storage = MagicMock(spec=Storage)
    migrations = [("v1", "CREATE TABLE test (id TEXT)")]
    storage.ensure_schema("path", "schema", migrations)
    assert storage.ensure_schema.called


def test_storage_protocol_register():
    """Storage implements register method."""
    storage = MagicMock(spec=Storage)
    storage.register("memory", "memory.db", "CREATE TABLE entries (...)")
    storage.register.assert_called_once()


def test_storage_protocol_migrations():
    """Storage implements migrations method."""
    storage = MagicMock(spec=Storage)
    migrations = [("v1", "ALTER TABLE...")]
    storage.migrations("memory", migrations)
    storage.migrations.assert_called_once()


def test_storage_protocol_ensure():
    """Storage implements ensure method."""
    storage = MagicMock(spec=Storage)
    storage.ensure("memory")
    storage.ensure.assert_called_once_with("memory")


def test_storage_protocol_migrate():
    """Storage implements migrate method."""
    storage = MagicMock(spec=Storage)
    conn = MagicMock()
    migrations = [("v1", "ALTER TABLE...")]
    storage.migrate(conn, migrations)
    storage.migrate.assert_called_once()


def test_storage_protocol_contract():
    """Storage protocol defines all required methods."""
    storage = MagicMock(spec=Storage)

    required_methods = ["connect", "ensure_schema", "register", "migrations", "ensure", "migrate"]
    for method in required_methods:
        assert hasattr(storage, method)
