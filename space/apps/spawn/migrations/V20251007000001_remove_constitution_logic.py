import sqlite3

def upgrade(cursor: sqlite3.Cursor):
    # Drop the constitutions table
    cursor.execute("DROP TABLE IF EXISTS constitutions")

    # Remove current_constitution_id from identities table
    # SQLite does not support DROP COLUMN, so we must recreate the table
    cursor.execute("ALTER TABLE identities RENAME TO _old_identities")
    cursor.execute("""
        CREATE TABLE identities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """
    )
    cursor.execute("INSERT INTO identities (id, type, created_at, updated_at) SELECT id, type, created_at, updated_at FROM _old_identities")
    cursor.execute("DROP TABLE _old_identities")

def downgrade(cursor: sqlite3.Cursor):
    # Recreate the constitutions table (simplified for downgrade)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS constitutions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            content TEXT NOT NULL,
            identity_id TEXT,
            created_at INTEGER NOT NULL,
            hash TEXT NOT NULL
        )
    """
    )
    # Recreate identities table with current_constitution_id (simplified for downgrade)
    cursor.execute("ALTER TABLE identities RENAME TO _new_identities")
    cursor.execute("""
        CREATE TABLE identities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            current_constitution_id TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (current_constitution_id) REFERENCES constitutions (id)
        )
    """
    )
    cursor.execute("INSERT INTO identities (id, type, created_at, updated_at) SELECT id, type, created_at, updated_at FROM _new_identities")
    cursor.execute("DROP TABLE _new_identities")
