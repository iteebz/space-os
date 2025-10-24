"""Security tests for events module SQL injection prevention."""

import sqlite3
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from space.os import events


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


class TestEventTableValidation:
    """Test table name validation in events module."""

    def test_valid_table_name(self):
        """Valid table name should pass validation."""
        events._validate_table("events")

    def test_invalid_table_name_with_semicolon(self):
        """Table name with SQL injection should fail."""
        with pytest.raises(ValueError, match="Invalid table"):
            events._validate_table("events; DROP TABLE users")

    def test_invalid_table_name_with_quotes(self):
        """Table name with quotes should fail."""
        with pytest.raises(ValueError, match="Invalid table"):
            events._validate_table("events' OR '1'='1")

    def test_invalid_table_name_different_table(self):
        """Non-whitelisted table should fail."""
        with pytest.raises(ValueError, match="Invalid table"):
            events._validate_table("users")

    def test_invalid_table_name_empty(self):
        """Empty table name should fail."""
        with pytest.raises(ValueError, match="Invalid table"):
            events._validate_table("")


class TestAddColumnValidation:
    """Test column validation in migration functions."""

    def test_valid_column_addition(self, temp_db):
        """Valid column should be added successfully."""
        conn = sqlite3.connect(temp_db)
        conn.execute("CREATE TABLE events (id TEXT)")
        conn.commit()

        events._add_column_if_not_exists(conn, "events", "agent_id", "TEXT")

        cursor = conn.execute("PRAGMA table_info(events)")
        cols = {row[1] for row in cursor.fetchall()}
        assert "agent_id" in cols
        conn.close()

    def test_invalid_table_in_add_column(self, temp_db):
        """Invalid table name should be rejected."""
        conn = sqlite3.connect(temp_db)
        with pytest.raises(ValueError, match="Invalid table"):
            events._add_column_if_not_exists(conn, "events; DROP TABLE x", "col", "TEXT")
        conn.close()

    def test_invalid_column_name(self, temp_db):
        """Invalid column name should be rejected."""
        conn = sqlite3.connect(temp_db)
        conn.execute("CREATE TABLE events (id TEXT)")
        conn.commit()

        with pytest.raises(ValueError, match="Invalid column"):
            events._add_column_if_not_exists(conn, "events", "col'; DROP TABLE x", "TEXT")
        conn.close()

    def test_invalid_column_type(self, temp_db):
        """Invalid type should be rejected."""
        conn = sqlite3.connect(temp_db)
        conn.execute("CREATE TABLE events (id TEXT)")
        conn.commit()

        with pytest.raises(ValueError, match="Invalid column"):
            events._add_column_if_not_exists(conn, "events", "newcol", "TEXT); DROP TABLE x; --")
        conn.close()

    def test_column_already_exists(self, temp_db):
        """Existing column should be skipped gracefully."""
        conn = sqlite3.connect(temp_db)
        conn.execute("CREATE TABLE events (id TEXT, agent_id TEXT)")
        conn.commit()

        events._add_column_if_not_exists(conn, "events", "agent_id", "TEXT")

        cursor = conn.execute("PRAGMA table_info(events)")
        cols = [row[1] for row in cursor.fetchall()]
        assert cols.count("agent_id") == 1
        conn.close()


class TestIdentifierValidator:
    """Test Python identifier validation for column/type names."""

    def test_valid_identifier(self):
        """Valid identifiers should pass."""
        assert "agent_id".isidentifier()
        assert "chat_id".isidentifier()
        assert "timestamp".isidentifier()

    def test_invalid_identifier_with_space(self):
        """Identifiers with spaces should fail."""
        assert not "agent id".isidentifier()

    def test_invalid_identifier_with_sql(self):
        """SQL injection in identifier should fail."""
        assert not "agent_id; DROP".isidentifier()
        assert not "agent_id' OR".isidentifier()

    def test_type_with_spaces_allowed(self):
        """Column types with spaces (like VARCHAR 255) need custom handling."""
        type_str = "VARCHAR 255"
        type_clean = type_str.replace(" ", "")
        assert type_clean.isidentifier()

    def test_sql_injection_in_type(self):
        """SQL injection in type should fail."""
        type_str = "TEXT); DROP TABLE x; --"
        type_clean = type_str.replace(" ", "")
        assert not type_clean.isidentifier()


class TestDataParameterization:
    """Test that data queries use parameterized statements."""

    def test_events_query_injection_attempt_safe(self):
        """Injection attempt in data parameter should be safe."""
        with mock.patch("space.os.events.DB_PATH") as mock_path:
            mock_path.exists.return_value = False
            malicious_source = "test' OR '1'='1"
            rows = events.query(source=malicious_source, limit=10)
            assert rows == []


class TestMigrationSecurity:
    """Test migration functions don't introduce vulnerabilities."""

    def test_migrate_add_agent_id(self, temp_db):
        """Should add agent_id column safely."""
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT,
                timestamp INTEGER NOT NULL
            )
        """)
        conn.commit()

        events._migrate_add_agent_id(conn)

        cursor = conn.execute("PRAGMA table_info(events)")
        cols = {row[1] for row in cursor.fetchall()}
        assert "agent_id" in cols
        conn.close()

    def test_migrate_add_chat_id(self, temp_db):
        """Should add chat_id column safely."""
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT,
                timestamp INTEGER NOT NULL
            )
        """)
        conn.commit()

        events._migrate_add_chat_id(conn)

        cursor = conn.execute("PRAGMA table_info(events)")
        cols = {row[1] for row in cursor.fetchall()}
        assert "chat_id" in cols
        conn.close()
