"""Session trace: full execution context and decision trail."""

from datetime import datetime

from space.lib.ids import truncate_uuid
from space.os import bridge, memory, spawn


def trace_session(session_id: str) -> dict:
    """Get complete context for a session: why it spawned, what it did, outcome.

    Args:
        session_id: Session UUID or short form

    Returns:
        Dict with full execution context
    """
    session = spawn.get_session(session_id)
    if not session:
        raise ValueError(f"Session '{session_id}' not found")

    agent_id = session.agent_id
    status = session.status
    started_at = session.created_at
    ended_at = session.ended_at
    input_text = session.input
    output_text = session.output
    stderr_text = session.stderr
    channel_id = session.channel_id
    triggered_by = session.triggered_by

    agent = spawn.get_agent(agent_id) if agent_id else None
    identity = agent.identity if agent else "unknown"

    last_message_in_channel = None
    if channel_id:
        messages = bridge.get_messages_before(channel_id, started_at, limit=1)
        if messages:
            msg = messages[0]
            last_message_in_channel = {
                "content": msg.content,
                "from_agent": msg.agent_id,
                "at": msg.created_at,
            }

    last_memory = None
    if agent_id:
        memories = memory.get_agent_memories(agent_id, after_timestamp=started_at, limit=1)
        if memories:
            mem = memories[0]
            last_memory = {
                "message": mem.message,
                "topic": mem.topic,
                "at": mem.created_at,
            }

    duration = None
    if started_at and ended_at:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        duration = (end - start).total_seconds()

    return {
        "type": "session",
        "session_id": session.id,
        "short_id": truncate_uuid(session.id),
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
