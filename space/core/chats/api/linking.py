from space.lib import db


def link(session_id: str, identity: str | None = None, task_id: str | None = None) -> None:
    """Link a chat session to an identity and/or task."""
    with db.ensure("chats") as conn:
        conn.execute(
            """
            UPDATE sessions 
            SET identity = ?, task_id = ?
            WHERE session_id = ?
            """,
            (identity, task_id, session_id),
        )


def get_by_identity(identity: str) -> list[dict]:
    """Get all sessions linked to an identity."""
    with db.ensure("chats") as conn:
        rows = conn.execute(
            """
            SELECT cli, session_id, file_path, task_id, discovered_at 
            FROM sessions 
            WHERE identity = ? 
            ORDER BY discovered_at DESC
            """,
            (identity,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_by_task_id(task_id: str) -> list[dict]:
    """Get all sessions linked to a task."""
    with db.ensure("chats") as conn:
        rows = conn.execute(
            """
            SELECT cli, session_id, file_path, identity, discovered_at 
            FROM sessions 
            WHERE task_id = ? 
            ORDER BY discovered_at DESC
            """,
            (task_id,),
        ).fetchall()
        return [dict(row) for row in rows]
