"""Trace API: unified execution introspection and diagnostics."""

from datetime import datetime

from space.os import bridge, spawn


def trace_agent(identity: str, limit: int = 10) -> dict:
    """Get agent info and spawn history."""
    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")

    agent_id = agent.agent_id
    spawns_list = spawn.get_spawns_for_agent(agent_id)

    recent_spawns = []
    for spawn_obj in spawns_list[-limit:]:
        recent_spawns.append(
            {
                "spawn_id": spawn_obj.id[:8],
                "status": spawn_obj.status,
                "created_at": spawn_obj.created_at,
                "ended_at": spawn_obj.ended_at,
            }
        )

    return {
        "type": "identity",
        "agent_id": agent_id,
        "identity": identity,
        "model": agent.model,
        "constitution": agent.constitution,
        "spawn_count": agent.spawn_count,
        "last_active_at": agent.last_active_at,
        "recent_spawns": recent_spawns,
    }


def trace_channel(channel_id: str) -> dict:
    """Get channel info and participant activity."""
    channel = bridge.get_channel(channel_id)
    if not channel:
        raise ValueError(f"Channel '{channel_id}' not found")

    messages = bridge.get_messages(channel.channel_id)

    # Build agent_id -> identity lookup
    from space.os.spawn.api import agents as spawn_agents

    agent_id_to_identity = {}
    for msg in messages:
        if msg.agent_id not in agent_id_to_identity:
            agent = spawn_agents.get_agent(msg.agent_id)
            agent_id_to_identity[msg.agent_id] = agent.identity if agent else "unknown"

    # Track last message per participant
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
            "identity": agent_id_to_identity.get(agent_id, "unknown"),
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
        "channel_id": channel.channel_id,
        "channel_name": channel.name,
        "participants": participants,
    }


def trace_spawn(spawn_id: str) -> dict:
    """Get spawn execution context with synced session data."""
    spawn_obj = spawn.api.get_spawn(spawn_id)
    if not spawn_obj:
        raise ValueError(f"Spawn '{spawn_id}' not found")

    if spawn_obj.session_id:
        try:
            from space.os.sessions.api import sync

            sync.ingest(spawn_obj.session_id)
        except Exception:
            pass

    agent = spawn.get_agent(spawn_obj.agent_id) if spawn_obj.agent_id else None
    identity = agent.identity if agent else "unknown"

    duration = None
    if spawn_obj.created_at and spawn_obj.ended_at:
        start = datetime.fromisoformat(spawn_obj.created_at)
        end = datetime.fromisoformat(spawn_obj.ended_at)
        duration = (end - start).total_seconds()

    return {
        "type": "session",
        "spawn_id": spawn_obj.id[:8],
        "session_id": spawn_obj.session_id,
        "identity": identity,
        "status": spawn_obj.status,
        "created_at": spawn_obj.created_at,
        "ended_at": spawn_obj.ended_at,
        "duration_seconds": duration,
        "channel_id": spawn_obj.channel_id,
        "is_ephemeral": spawn_obj.is_ephemeral,
    }


def _parse_explicit_query(query: str) -> tuple[str, str] | None:
    """Parse explicit prefix syntax: agent:<name>, session:<id>, channel:<name|id>.

    Returns: (type, value) or None if no prefix
    """
    if ":" not in query:
        return None

    prefix, value = query.split(":", 1)
    if not value:
        raise ValueError(f"Empty query after prefix '{prefix}:'")

    prefix = prefix.lower()
    if prefix in ("agent", "a"):
        return ("identity", value)
    if prefix in ("session", "s"):
        return ("session_id", value)
    if prefix in ("channel", "c"):
        return ("channel_id", value)

    raise ValueError(f"Unknown prefix '{prefix}'. Use agent:, session:, or channel:")


def _identify_implicit_query(query: str) -> tuple[str, str]:
    """Fallback: infer query type from content (agent name, spawn_id, session UUID, or channel).

    Returns: (type, normalized_query)
    """
    agent = spawn.get_agent(query)
    if agent:
        return ("identity", agent.identity)

    spawn_obj = spawn.api.get_spawn(query)
    if spawn_obj:
        return ("spawn_id", spawn_obj.id)

    try:
        channel = bridge.get_channel(query)
        if channel:
            return ("channel_id", channel.channel_id)
    except (ValueError, KeyError):
        pass

    return ("unknown", query)


def identify_query_type(query: str) -> tuple[str, str]:
    """Parse query with optional explicit prefix, fallback to implicit inference.

    Syntax:
    - Explicit: agent:zealot, session:7a6a07de, channel:general
    - Implicit: zealot (infers agent), 7a6a07de (infers session), general (infers channel)

    Returns: (type, normalized_query)

    Raises:
        ValueError: If query malformed or not found
    """
    explicit = _parse_explicit_query(query)
    if explicit:
        query_type, value = explicit
        if query_type == "identity":
            agent = spawn.get_agent(value)
            if not agent:
                raise ValueError(f"Agent '{value}' not found")
            return (query_type, agent.identity)
        if query_type == "session_id":
            try:
                trace_spawn(value)
            except ValueError as e:
                raise ValueError(f"Session '{value}' not found") from e
            return (query_type, value)
        if query_type == "channel_id":
            channel = bridge.get_channel(value)
            if channel:
                return (query_type, channel.channel_id)
            raise ValueError(f"Channel '{value}' not found")

    query_type, normalized = _identify_implicit_query(query)
    if query_type == "unknown":
        raise ValueError(
            f"Query '{query}' not found or ambiguous. "
            f"Use explicit prefix: agent:NAME, session:ID, or channel:NAME"
        )

    return (query_type, normalized)


def trace(query: str) -> dict:
    """Unified trace interface: parse query and route to handler.

    Args:
        query: agent:NAME, session:ID, channel:NAME, or implicit value

    Returns:
        Dict with type-specific context

    Raises:
        ValueError: If query malformed or not found
    """
    query_type, normalized = identify_query_type(query)

    if query_type == "identity":
        return trace_agent(normalized)
    if query_type == "spawn_id":
        return trace_spawn(normalized)
    if query_type == "session_id":
        return trace_spawn(normalized)
    if query_type == "channel_id":
        return trace_channel(normalized)
    return None


__all__ = [
    "trace",
    "trace_agent",
    "trace_channel",
    "trace_spawn",
    "identify_query_type",
]
