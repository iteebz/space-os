"""Handoff operations: create, close, list pending."""

from datetime import datetime

from space.core.models import Handoff, HandoffStatus
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7

from .channels import _to_channel_id, get_channel


def _row_to_handoff(row: store.Row) -> Handoff:
    return from_row(row, Handoff)


def create_handoff(channel: str, from_identity: str, to_identity: str, summary: str) -> Handoff:
    """Create handoff with dual-write (handoffs table + channel message)."""
    from space.os import spawn

    channel_id = _to_channel_id(channel)
    channel_obj = get_channel(channel_id)
    if not channel_obj:
        raise ValueError(f"Channel '{channel}' not found.")

    from_agent = spawn.get_agent(from_identity)
    if not from_agent:
        raise ValueError(f"Identity '{from_identity}' not registered.")

    to_agent = spawn.get_agent(to_identity)
    if not to_agent:
        raise ValueError(f"Identity '{to_identity}' not registered.")

    handoff_id = uuid7()
    message_id = uuid7()
    message_content = f"@{to_identity} handoff: {summary}"

    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO messages (message_id, channel_id, agent_id, content) VALUES (?, ?, ?, ?)",
            (message_id, channel_obj.channel_id, from_agent.agent_id, message_content),
        )
        conn.execute(
            """INSERT INTO handoffs
            (handoff_id, channel_id, from_agent, to_agent, summary, message_id)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                handoff_id,
                channel_obj.channel_id,
                from_agent.agent_id,
                to_agent.agent_id,
                summary,
                message_id,
            ),
        )

    spawn.touch_agent(from_agent.agent_id)

    return get_handoff(handoff_id)


def close_handoff(handoff_id: str) -> Handoff | None:
    """Close a pending handoff."""
    handoff = get_handoff(handoff_id)
    if not handoff:
        return None

    if handoff.status == HandoffStatus.CLOSED:
        return handoff

    now = datetime.now().isoformat()
    with store.ensure() as conn:
        conn.execute(
            "UPDATE handoffs SET status = ?, closed_at = ? WHERE handoff_id = ?",
            (HandoffStatus.CLOSED.value, now, handoff_id),
        )

    return get_handoff(handoff_id)


def get_handoff(handoff_id: str) -> Handoff | None:
    """Get handoff by ID (supports prefix match)."""
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT handoff_id, channel_id, from_agent, to_agent, summary, message_id, status, created_at, closed_at FROM handoffs WHERE handoff_id = ?",
            (handoff_id,),
        ).fetchone()
        if row:
            return _row_to_handoff(row)

        row = conn.execute(
            "SELECT handoff_id, channel_id, from_agent, to_agent, summary, message_id, status, created_at, closed_at FROM handoffs WHERE handoff_id LIKE ?",
            (f"{handoff_id}%",),
        ).fetchone()
        return _row_to_handoff(row) if row else None


def list_pending(to_identity: str | None = None, channel: str | None = None) -> list[Handoff]:
    """List pending handoffs, optionally filtered by recipient and/or channel."""
    from space.os import spawn

    query = "SELECT handoff_id, channel_id, from_agent, to_agent, summary, message_id, status, created_at, closed_at FROM handoffs WHERE status = ?"
    params: list[str] = [HandoffStatus.PENDING.value]

    if to_identity:
        agent = spawn.get_agent(to_identity)
        if not agent:
            raise ValueError(f"Identity '{to_identity}' not registered.")
        query += " AND to_agent = ?"
        params.append(agent.agent_id)

    if channel:
        channel_id = _to_channel_id(channel)
        channel_obj = get_channel(channel_id)
        if not channel_obj:
            raise ValueError(f"Channel '{channel}' not found.")
        query += " AND channel_id = ?"
        params.append(channel_obj.channel_id)

    query += " ORDER BY created_at"

    with store.ensure() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_handoff(row) for row in rows]


def list_handoffs_for_channel(channel: str) -> list[Handoff]:
    """List all handoffs in a channel."""
    channel_id = _to_channel_id(channel)
    channel_obj = get_channel(channel_id)
    if not channel_obj:
        raise ValueError(f"Channel '{channel}' not found.")

    with store.ensure() as conn:
        rows = conn.execute(
            "SELECT handoff_id, channel_id, from_agent, to_agent, summary, message_id, status, created_at, closed_at FROM handoffs WHERE channel_id = ? ORDER BY created_at",
            (channel_obj.channel_id,),
        ).fetchall()
        return [_row_to_handoff(row) for row in rows]
