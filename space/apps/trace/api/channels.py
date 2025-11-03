"""Channel trace: active agents and participation history."""

from space.core import db
from space.lib import store


def trace_channel(channel_id: str) -> dict:
    """Get agents active in channel with their recent activity.

    Args:
        channel_id: Channel UUID or name

    Returns:
        Dict with channel info and participant activity
    """
    with store.ensure("bridge") as conn:
        channel_row = conn.execute(
            "SELECT channel_id, name FROM channels WHERE channel_id = ? OR name = ?",
            (channel_id, channel_id),
        ).fetchone()

        if not channel_row:
            raise ValueError(f"Channel '{channel_id}' not found")

        actual_channel_id = channel_row[0]

        agent_messages = conn.execute(
            """
            SELECT agent_id, content, created_at,
                   ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at DESC) as rn
            FROM messages
            WHERE channel_id = ?
            """,
            (actual_channel_id,),
        ).fetchall()

    db.register()
    with db.connect() as conn:
        agents_map = {
            row[0]: row[1]
            for row in conn.execute("SELECT agent_id, identity FROM agents").fetchall()
        }

    participant_data = {}
    for agent_id, content, created_at, rn in agent_messages:
        if agent_id not in participant_data:
            participant_data[agent_id] = {
                "last_message_at": created_at,
                "last_message": content[:60] if rn == 1 else None,
            }

    participants = [
        {
            "agent_id": agent_id,
            "identity": agents_map.get(agent_id, "unknown"),
            "last_message_at": data["last_message_at"],
            "last_message": data["last_message"],
        }
        for agent_id, data in sorted(
            participant_data.items(),
            key=lambda x: x[1]["last_message_at"],
            reverse=True,
        )
    ]

    return {
        "type": "channel",
        "channel_id": actual_channel_id,
        "channel_name": channel_row[1],
        "participants": participants,
    }
