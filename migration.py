#!/usr/bin/env python

import hashlib
import sqlite3
from pathlib import Path

BACKUP_DB_PATH = Path("/Users/teebz/dev/space/20251006_194600/spawn.db")
NEW_DB_PATH = Path("/Users/teebz/dev/space/private/agent-space/space/spawn.db")
GUIDES_DIR = Path("/Users/teebz/dev/space/private/agent-space/guides")

CONSTITUTIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS constitutions (
    hash TEXT PRIMARY KEY,
    content TEXT NOT NULL
);
"""

GUIDES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS guides (
    name TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

REGISTRY_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    channels TEXT NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    constitution_hash TEXT NOT NULL,
    self_description TEXT,
    provider TEXT,
    model TEXT,
    FOREIGN KEY (constitution_hash) REFERENCES constitutions (hash)
);
"""

def migrate():
    """Migrates the data from the old spawn.db and guide files to the new spawn.db."""
    if not BACKUP_DB_PATH.exists():
        print(f"Backup database not found at {BACKUP_DB_PATH}")
        return

    new_db_conn = sqlite3.connect(NEW_DB_PATH)
    new_db_conn.execute("PRAGMA foreign_keys = ON;")
    new_db_conn.execute(CONSTITUTIONS_TABLE_SCHEMA)
    new_db_conn.execute(GUIDES_TABLE_SCHEMA)
    new_db_conn.execute(REGISTRY_TABLE_SCHEMA)

    # Migrate registry
    backup_db_conn = sqlite3.connect(BACKUP_DB_PATH)
    backup_db_conn.row_factory = sqlite3.Row
    old_registry_rows = backup_db_conn.execute("SELECT * FROM registrations").fetchall()

    for row in old_registry_rows:
        identity_content = row["identity"]
        identity_hash = hashlib.sha256(identity_content.encode()).hexdigest()

        # Insert into constitutions table
        new_db_conn.execute(
            "INSERT OR IGNORE INTO constitutions (hash, content) VALUES (?, ?)",
            (identity_hash, identity_content),
        )

        # Insert into new registry table
        new_db_conn.execute(
            """INSERT INTO registry 
                (agent_id, role, channels, registered_at, constitution_hash, self_description, provider, model) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["agent_id"],
                row["role"],
                row["channels"],
                row["registered_at"],
                identity_hash,
                row["self"],
                row.get("provider"),
                row.get("model"),
            ),
        )

    # Migrate guides
    if GUIDES_DIR.exists():
        for guide_file in GUIDES_DIR.glob("*.md"):
            content = guide_file.read_text()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            new_db_conn.execute(
                "INSERT OR REPLACE INTO guides (name, content, hash) VALUES (?, ?, ?)",
                (guide_file.stem, content, content_hash),
            )

    new_db_conn.commit()
    new_db_conn.close()
    backup_db_conn.close()

    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
