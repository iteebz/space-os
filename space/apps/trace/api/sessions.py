"""Session trace: full execution context and decision trail."""

from space.core import db
from space.lib import store
from space.lib.ids import truncate_uuid
from space.os import spawn


def trace_session(session_id: str) -> dict:
    """Get complete context for a session: why it spawned, what it did, outcome.

    Args:
        session_id: Session UUID or short form

    Returns:
        Dict with full execution context
    """
    db.register()

    with db.connect() as conn:
        session_row = conn.execute(
            """
            SELECT session_id, agent_id, status, started_at, ended_at,
                   input, output, stderr, channel_id, triggered_by, chat_id
            FROM sessions WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()

        if not session_row:
            raise ValueError(f"Session '{session_id}' not found")

        agent_id = session_row[1]
        status = session_row[2]
        started_at = session_row[3]
        ended_at = session_row[4]
        input_text = session_row[5]
        output_text = session_row[6]
        stderr_text = session_row[7]
        channel_id = session_row[8]
        triggered_by = session_row[9]

        agent = spawn.get_agent(agent_id) if agent_id else None
        identity = agent.identity if agent else "unknown"

    last_message_in_channel = None
    if channel_id:
        with store.ensure("bridge") as conn:
            msg_row = conn.execute(
                """
                SELECT content, agent_id, created_at FROM messages
                WHERE channel_id = ? AND created_at < ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (channel_id, started_at),
            ).fetchone()
            if msg_row:
                last_message_in_channel = {
                    "content": msg_row[0],
                    "from_agent": msg_row[1],
                    "at": msg_row[2],
                }

    last_memory = None
    if agent_id:
        with store.ensure("memory") as conn:
            mem_row = conn.execute(
                """
                SELECT message, topic, created_at FROM memories
                WHERE agent_id = ? AND created_at > ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (agent_id, started_at),
            ).fetchone()
            if mem_row:
                last_memory = {
                    "message": mem_row[0],
                    "topic": mem_row[1],
                    "at": mem_row[2],
                }

    duration = None
    if started_at and ended_at:
        from datetime import datetime

        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        duration = (end - start).total_seconds()

    return {
        "type": "session",
        "session_id": session_id,
        "short_id": truncate_uuid(session_id),
        "identity": identity,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration,
        "triggered_by": triggered_by,
        "channel_id": channel_id,
        "channel_context": last_message_in_channel,
        "input": input_text,
        "output": output_text,
        "stderr": stderr_text,
        "last_memory_mutation": last_memory,
    }
