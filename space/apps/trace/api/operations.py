"""Trace dispatcher: routes queries to appropriate trace module."""

from space.apps.trace.api import agents, channels, sessions
from space.os import bridge, spawn


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
    """Fallback: infer query type from content (agent name, session UUID, or channel).

    Returns: (type, normalized_query)
    """
    agent = spawn.get_agent(query)
    if agent:
        return ("identity", agent.identity)

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
                sessions.trace_session(value)
            except ValueError as e:
                raise ValueError(f"Session '{value}' not found") from e
            return (query_type, value)
        if query_type == "channel_id":
            try:
                channel = bridge.get_channel(value)
                if channel:
                    return (query_type, channel.channel_id)
            except Exception:
                pass
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
        return agents.trace_agent(normalized)
    if query_type == "session_id":
        return sessions.trace_session(normalized)
    if query_type == "channel_id":
        return channels.trace_channel(normalized)
    return None
