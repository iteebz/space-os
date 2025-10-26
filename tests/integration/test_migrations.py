"""
Integration tests for database migrations across all modules.

Tests the contract: migrations apply correctly, are idempotent, and
create required schema.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from space.lib import store


@pytest.fixture
def temp_db_dir():
    """Temporary directory for test databases."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


def _test_module(module_path, db_name, required_tables, required_columns):
    """Helper to test a module's migration contract.

    Args:
        module_path: Import path like "space.core.memory"
        db_name: Database filename like "memory.db"
        required_tables: Set of table names that must exist
        required_columns: Dict[table_name, set of column names]
    """

    def test_impl(temp_db_dir):
        import importlib

        mod = importlib.import_module(module_path + ".db")
        temp_db_dir / db_name
        # Ensure the database is initialized and migrations are applied via store.ensure
        conn = store.ensure(module_path.split(".")[-1])

        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert required_tables <= tables, f"Missing tables: {required_tables - tables}"

        for table, cols in required_columns.items():
            cursor = conn.execute(f"PRAGMA table_info({table})")
            actual = {row[1] for row in cursor.fetchall()}
            assert cols <= actual, f"Table {table} missing columns: {cols - actual}"

        cursor = conn.execute("SELECT COUNT(*) FROM _migrations")
        mig_count = cursor.fetchone()[0]
        assert mig_count == len(mod.migrations.MIGRATIONS)

        # Ensure idempotency by calling ensure again
        store.ensure(module_path.split(".")[-1])
        cursor = conn.execute("SELECT COUNT(*) FROM _migrations")

        conn.close()

    return test_impl


test_memory_migrations = _test_module(
    "space.core.memory",
    "memory.db",
    {"memories", "links"},
    {
        "memories": {"memory_id", "agent_id", "topic", "message", "created_at"},
        "links": {"link_id", "memory_id", "parent_id", "kind", "created_at"},
    },
)


test_bridge_migrations = _test_module(
    "space.core.bridge",
    "bridge.db",
    {"messages", "channels", "bookmarks", "notes"},
    {"messages": {"message_id", "channel_id", "content"}},
)


test_spawn_migrations = _test_module(
    "space.core.spawn",
    "spawn.db",
    {"agents", "tasks"},
    {"agents": {"agent_id", "identity"}, "tasks": {"task_id", "agent_id", "input"}},
)


test_knowledge_migrations = _test_module(
    "space.core.knowledge",
    "knowledge.db",
    {"knowledge"},
    {"knowledge": {"knowledge_id", "domain", "content"}},
)
