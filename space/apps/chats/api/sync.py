from datetime import datetime
from pathlib import Path

from space.lib import providers, store


def get_sync_state(cli: str, session_id: str) -> dict | None:
    """Get sync state for a session."""
    with store.ensure("chats") as conn:
        row = conn.execute(
            """
            SELECT last_byte_offset, last_synced_at, is_complete
            FROM syncs
            WHERE cli = ? AND session_id = ?
            """,
            (cli, session_id),
        ).fetchone()
        if row:
            return dict(row)
    return None


def update_sync_state(
    cli: str, session_id: str, byte_offset: int, is_complete: bool = False
) -> None:
    """Update sync state after syncing messages."""
    with store.ensure("chats") as conn:
        conn.execute(
            """
            UPDATE syncs
            SET last_byte_offset = ?, last_synced_at = ?, is_complete = ?
            WHERE cli = ? AND session_id = ?
            """,
            (byte_offset, datetime.now().isoformat(), is_complete, cli, session_id),
        )


def sync(session_id: str | None = None, identity: str | None = None, cli: str | None = None) -> int:
    """
    Sync chat(s) from offset. Track sync state only (raw JSONL is source of truth).

    Args:
        session_id: Sync specific session
        identity: Sync all sessions linked to identity
        cli: Sync all sessions for specific provider (claude, codex, gemini)

    Returns:
        Total messages synced
    """
    total_synced = 0

    with store.ensure("chats") as conn:
        if session_id:
            sessions = conn.execute(
                "SELECT cli, session_id, file_path FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        elif identity:
            sessions = conn.execute(
                "SELECT cli, session_id, file_path FROM sessions WHERE identity = ?",
                (identity,),
            ).fetchall()
        elif cli:
            sessions = conn.execute(
                "SELECT cli, session_id, file_path FROM sessions WHERE cli = ?",
                (cli,),
            ).fetchall()
        else:
            sessions = conn.execute("SELECT cli, session_id, file_path FROM sessions").fetchall()

        for session_row in sessions:
            cli_name = session_row["cli"]
            sess_id = session_row["session_id"]
            file_path = session_row["file_path"]

            if not Path(file_path).exists():
                continue

            sync_state = get_sync_state(cli_name, sess_id)
            offset = sync_state["last_byte_offset"] if sync_state else 0

            provider = getattr(providers, cli_name, None)
            if not provider:
                continue

            try:
                messages = provider.parse_messages(Path(file_path), from_offset=offset)

                if messages:
                    final_offset = messages[-1].get("byte_offset", offset)
                    update_sync_state(cli_name, sess_id, final_offset)
                    total_synced += len(messages)
            except Exception as e:
                import logging

                logging.error(f"Sync error {cli_name}/{sess_id}: {e}")
                pass

    return total_synced
