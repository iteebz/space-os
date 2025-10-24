import sqlite3


def _migrate_id_to_knowledge_id(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(knowledge)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "id" in cols and "knowledge_id" not in cols:
        conn.execute("ALTER TABLE knowledge RENAME COLUMN id TO knowledge_id")


MIGRATIONS = [
    ("migrate_id_to_knowledge_id", _migrate_id_to_knowledge_id),
]
