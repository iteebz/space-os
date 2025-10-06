def upgrade(cursor):
    cursor.execute("""
        CREATE TABLE knowledge (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            contributor TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL,
            created_at TEXT NOT NULL
        )
    """)

def downgrade(cursor):
    cursor.execute("DROP TABLE knowledge")