from __future__ import annotations

import importlib.util
import sqlite3
from collections.abc import Callable
from pathlib import Path

def get_current_schema_version(conn: sqlite3.Connection) -> int:
    """Retrieves the current schema version from the database using PRAGMA user_version."""
    cursor = conn.execute("PRAGMA user_version;")
    return cursor.fetchone()[0]

def update_schema_version(conn: sqlite3.Connection, version: int):
    """Updates the schema version in the database using PRAGMA user_version."""
    conn.execute(f"PRAGMA user_version = {version};")

def apply_migration(conn: sqlite3.Connection, schema_file_path: Path):
    """Applies a single Python migration file by dynamically loading and executing its 'migrate' function."""
    spec = importlib.util.spec_from_file_location(schema_file_path.stem, schema_file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'migrate') and callable(module.migrate):
            module.migrate(conn)
        else:
            raise AttributeError(f"Migration file {schema_file_path} must contain a callable 'migrate' function.")
    else:
        raise ImportError(f"Could not load migration file {schema_file_path}.")

def ensure_schema(conn: sqlite3.Connection, app_root_path: Path, schema_files: list[str]):
    """
    Ensures the database schema is up-to-date by applying migrations.
    This function is passed as the initializer to app.ensure_db().
    """
    current_version = get_current_schema_version(conn)
    migrations_dir = app_root_path / "schemas" # Assuming schemas are in app_root_path/schemas

    for i, schema_name in enumerate(schema_files):
        migration_version = i + 1
        if migration_version > current_version:
            schema_file = migrations_dir / schema_name
            print(f"Applying migration: {schema_file}") # For debugging/logging
            try:
                apply_migration(conn, schema_file)
                update_schema_version(conn, migration_version)
            except Exception as e:
                print(f"Error applying migration {schema_file}: {e}")
                raise # Re-raise to ensure transaction rollback if ensure_db is used in a transaction
