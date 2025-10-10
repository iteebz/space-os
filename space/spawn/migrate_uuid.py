"""Migrate name strings to agent_id UUIDs."""
import sqlite3

from ..lib import paths
from . import registry


def backfill():
    """Backfill agent_id from names."""
    registry.init_db()

    with registry.get_db() as conn:
        name_map = {row[1]: row[0] for row in conn.execute("SELECT id, name FROM agents")}

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

        rows = conn.execute(
            f"SELECT rowid, {name_col} FROM {table} WHERE agent_id IS NULL AND {name_col} IS NOT NULL"
        ).fetchall()

        updated = 0
        for row in rows:
            name = row[name_col]
            uuid = name_map.get(name)
            if uuid:
                conn.execute(f"UPDATE {table} SET agent_id = ? WHERE rowid = ?", (uuid, row[0]))
                updated += 1

        conn.commit()
        conn.close()
        print(f"✓ {table}.{name_col} → agent_id ({updated} rows)")


if __name__ == "__main__":
    backfill()
