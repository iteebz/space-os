from datetime import datetime
from pathlib import Path

from space.lib import db

from . import providers


def get_sync_state(cli: str, session_id: str) -> dict | None:
    """Get sync state for a session."""
    with db.ensure("chats") as conn:
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


def update_sync_state(cli: str, session_id: str, byte_offset: int, is_complete: bool = False) -> None:
    """Update sync state after syncing messages."""
    with db.ensure("chats") as conn:
        conn.execute(
            """
            UPDATE syncs 
            SET last_byte_offset = ?, last_synced_at = ?, is_complete = ?
            WHERE cli = ? AND session_id = ?
            """,
            (byte_offset, datetime.now().isoformat(), is_complete, cli, session_id),
        )


def sync(session_id: str | None = None, identity: str | None = None) -> int:
    """
    Sync chat(s) from offset. Returns number of messages synced.
    
    Args:
        session_id: Sync specific session
        identity: Sync all sessions linked to identity
    
    Returns:
        Total messages synced
    """
    if not session_id and not identity:
        raise ValueError("Must provide session_id or identity")
    
    total_synced = 0
    
    with db.ensure("chats") as conn:
        if session_id:
            sessions = conn.execute(
                "SELECT cli, session_id, file_path FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        else:
            sessions = conn.execute(
                "SELECT cli, session_id, file_path FROM sessions WHERE identity = ?",
                (identity,),
            ).fetchall()
        
        for session_row in sessions:
            cli = session_row["cli"]
            sess_id = session_row["session_id"]
            file_path = session_row["file_path"]
            
            sync_state = get_sync_state(cli, sess_id)
            if not sync_state or not Path(file_path).exists():
                continue
            
            provider = providers.get_provider(cli)
            if not provider:
                continue
            
            try:
                messages = provider.parse_messages(
                    Path(file_path),
                    from_offset=sync_state["last_byte_offset"]
                )
                
                if messages:
                    final_offset = messages[-1].get("byte_offset", sync_state["last_byte_offset"])
                    update_sync_state(cli, sess_id, final_offset)
                    total_synced += len(messages)
            except Exception:
                pass
    
    return total_synced
