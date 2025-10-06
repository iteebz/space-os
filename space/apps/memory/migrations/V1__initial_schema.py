import sqlite3

def upgrade(cursor: sqlite3.Cursor):
    """
    Create the initial 'memory' table.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            uuid TEXT PRIMARY KEY,
            identity TEXT NOT NULL,
            topic TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

def downgrade(cursor: sqlite3.Cursor):
    """
    Drop the 'memory' table.
    """
    cursor.execute("DROP TABLE IF EXISTS memory")
