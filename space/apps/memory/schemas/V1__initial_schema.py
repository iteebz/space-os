import sqlite3

def migrate(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            uuid TEXT PRIMARY KEY,
            identity TEXT NOT NULL,
            topic TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at REAL NOT NULL
        );
    """)
