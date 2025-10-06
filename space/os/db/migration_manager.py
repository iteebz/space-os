import sqlite3
from pathlib import Path
import re
from dataclasses import dataclass
from typing import Callable
import importlib.util
import sys

# Define the root directory for all app migrations
MIGRATIONS_ROOT = Path(__file__).parent / "migrations"

@dataclass(frozen=True)
class Migration:
    version: str
    filename: Path
    upgrade: Callable[[sqlite3.Cursor], None] | None = None
    downgrade: Callable[[sqlite3.Cursor], None] | None = None

def init_migrations_table(conn: sqlite3.Connection):
    """
    Ensures the _migrations table exists in the given database connection.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def get_applied_migrations(conn: sqlite3.Connection) -> set[str]:
    """
    Retrieves a set of applied migration versions from the _migrations table.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM _migrations")
    return {row[0] for row in cursor.fetchall()}

def get_available_migrations(app_name: str) -> list[Migration]:
    """
    Discovers and returns a sorted list of available migrations for a given app.
    """
    app_migrations_dir = MIGRATIONS_ROOT / app_name
    if not app_migrations_dir.is_dir():
        return []

    migrations = []
    migration_pattern = re.compile(r"^(V\d{14}_.*)\.py$")

    for f in app_migrations_dir.iterdir():
        if f.is_file() and f.suffix == ".py":
            match = migration_pattern.match(f.name)
            if match:
                version = match.group(1) # Capture the full version string
                migrations.append(Migration(version=version, filename=f))

    # Sort migrations by version (timestamp part of the version string)
    migrations.sort(key=lambda m: m.version)
    return migrations

def apply_migrations(app_name: str, conn: sqlite3.Connection):
    """
    Applies all pending migrations for a given app.
    """
    init_migrations_table(conn)
    applied_versions = get_applied_migrations(conn)
    available_migrations = get_available_migrations(app_name)

    for migration in available_migrations:
        if migration.version not in applied_versions:
            # Dynamically load the migration module
            spec = importlib.util.spec_from_file_location(migration.version, migration.filename)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[migration.version] = module # Add to sys.modules to prevent re-import issues
                spec.loader.exec_module(module)

                if hasattr(module, "upgrade") and callable(module.upgrade):
                    cursor = conn.cursor()
                    try:
                        module.upgrade(cursor)
                        cursor.execute("INSERT INTO _migrations (version) VALUES (?) ", (migration.version,))
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        print(f"Error applying migration {migration.version}: {e}")
                        raise
                else:
                    print(f"Migration {migration.version} is missing an 'upgrade' function.")
            else:
                print(f"Could not load migration module {migration.version}")