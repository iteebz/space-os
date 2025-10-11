"""Migrate name strings to agent_id UUIDs."""

import sqlite3

from .. import events as events_db
from ..bridge import db as bridge_db
from ..knowledge import db as knowledge_db
from ..lib import paths
from ..memory import db as memory_db
from . import registry


def migrate():
    registry.init_db()

    # Ensure all databases have their schemas migrated
    bridge_db._connect()
    memory_db.connect()
    knowledge_db.connect()
    events_db._connect()

    # Load name→uuid map
    with registry.get_db() as conn:
        name_to_uuid = {row[1]: row[0] for row in conn.execute("SELECT id, name FROM agents")}

    # Migrate each database
    dbs = [
        (paths.space_root() / "bridge.db", "messages", "sender"),
        (paths.space_root() / "memory.db", "memory", "identity"),
        (paths.space_root() / "knowledge.db", "knowledge", "contributor"),
        (paths.space_root() / "events.db", "events", "identity"),
    ]

    for db_path, table, name_col in dbs:
        if not db_path.exists():
            continue

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        for row in conn.execute(f"SELECT rowid, {name_col} FROM {table} WHERE agent_id IS NULL"):
            name = row[name_col]
            uuid = name_to_uuid.get(name)
            if uuid:
                conn.execute(f"UPDATE {table} SET agent_id = ? WHERE rowid = ?", (uuid, row[0]))

        conn.commit()
        conn.close()
        print(f"✓ Migrated {table}.{name_col} → agent_id")


if __name__ == "__main__":
    migrate()
