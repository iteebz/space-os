import sqlite3


def _migrate_id_to_knowledge_id(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(knowledge)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "id" in cols and "knowledge_id" not in cols:
        conn.execute("ALTER TABLE knowledge RENAME COLUMN id TO knowledge_id")


def _add_archived_at_column(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(knowledge)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "archived_at" not in cols:
        conn.execute("ALTER TABLE knowledge ADD COLUMN archived_at INTEGER")


MIGRATIONS = [
    ("migrate_id_to_knowledge_id", _migrate_id_to_knowledge_id),
    ("add_archived_at_column", _add_archived_at_column),
]
