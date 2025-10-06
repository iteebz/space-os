def upgrade(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            event_type TEXT NOT NULL,
            identity TEXT,
            data TEXT,
            metadata TEXT
        )
    """)

def downgrade(cursor):
    cursor.execute("DROP TABLE events")