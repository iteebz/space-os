"""Channel trace: active agents and participation history."""

from space.os import bridge, spawn


def trace_channel(channel_id: str) -> dict:
    """Get agents active in channel with their recent activity.

    Args:
        channel_id: Channel UUID or name

    Returns:
        Dict with channel info and participant activity
    """
    channel = bridge.get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel '{channel_id}' not found")

    actual_channel_id = channel.channel_id
    channel_name = channel.name

    messages = bridge.get_messages(actual_channel_id)
    agents_list = spawn.list_agents()
    agents_map = {agent.agent_id: agent.identity for agent in agents_list}

    participant_data = {}
    for msg in messages:
        if msg.agent_id not in participant_data:
            participant_data[msg.agent_id] = {
                "last_message_at": msg.created_at,
                "last_message": msg.content[:60],
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
        "channel_name": channel_name,
        "participants": participants,
    }
