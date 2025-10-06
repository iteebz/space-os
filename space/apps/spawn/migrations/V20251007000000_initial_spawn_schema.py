import sqlite3

def upgrade(cursor: sqlite3.Cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS identities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            current_constitution_id TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (current_constitution_id) REFERENCES constitutions (id)
        )
    """
    )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS constitutions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            content TEXT NOT NULL,
            identity_id TEXT,
            previous_version_id TEXT,
            created_at INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            change_description TEXT,
            hash TEXT NOT NULL, -- Add hash column
            FOREIGN KEY (identity_id) REFERENCES identities (id),
            FOREIGN KEY (previous_version_id) REFERENCES constitutions (id)
        )
    """
    )

def downgrade(cursor: sqlite3.Cursor):
    cursor.execute("DROP TABLE IF EXISTS constitutions")
    cursor.execute("DROP TABLE IF EXISTS identities")