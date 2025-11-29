"""Session operations: search, statistics, and resolution."""

import logging

from space.core.models import SessionStats
from space.lib import store, uuid7

logger = logging.getLogger(__name__)


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search transcripts via FTS5 (implicit episodic memory).

    Args:
        query: Search query (supports FTS5 syntax: phrase, boolean, wildcards, NEAR)
        identity: Filter results to specific agent identity
        all_agents: Reserved for future multi-agent filtering

    Returns:
        List of results matching the query, sorted by BM25 relevance + recency.
        Each result has: source, cli, session_id, identity, role, text, timestamp, reference, score
    """
    results = []

    try:
        with store.ensure() as conn:
            where_clause = "WHERE fts.transcripts_fts MATCH ?"
            params = [query]

            if identity:
                where_clause += " AND t.identity = ?"
                params.append(identity)

            rows = conn.execute(
                f"""
                SELECT
                    t.session_id,
                    t.provider,
                    t.type,
                    t.identity,
                    t.content,
                    t.timestamp,
                    fts.rank
                FROM transcripts t
                JOIN transcripts_fts fts ON t.id = fts.rowid
                {where_clause}
                ORDER BY fts.rank, t.timestamp DESC
                LIMIT 100
                """,
                params,
            ).fetchall()

            for row in rows:
                session_id, provider, message_type, identity, content, timestamp, rank = row
                score = abs(rank)

                results.append(
                    {
                        "source": "chat",
                        "cli": provider,
                        "session_id": session_id,
                        "type": message_type,
                        "identity": identity,
                        "text": content,
                        "timestamp": timestamp,
                        "reference": session_id,
                        "score": score,
                    }
                )

    except Exception as e:
        logger.warning(f"Transcript search failed for query '{query}': {e}")

    return results[:50]


def get_stats() -> dict:
    """Get session statistics from sessions table.

    Returns aggregated session metrics by provider and agent.
    """
    with store.ensure() as conn:
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        totals = conn.execute(
            "SELECT COALESCE(SUM(message_count), 0), COALESCE(SUM(tool_count), 0), "
            "COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0) FROM sessions"
        ).fetchone()

        by_provider = conn.execute(
            "SELECT provider, COUNT(*), COALESCE(SUM(message_count), 0), "
            "COALESCE(SUM(tool_count), 0), COALESCE(SUM(input_tokens), 0), "
            "COALESCE(SUM(output_tokens), 0) FROM sessions GROUP BY provider"
        ).fetchall()

    def to_dict(row, keys):
        return {k: row[i] for i, k in enumerate(keys)}

    return {
        "total_sessions": total_sessions,
        "total_messages": totals[0],
        "total_tools_used": totals[1],
        "total_input_tokens": totals[2],
        "total_output_tokens": totals[3],
        "by_provider": {
            row[0]: to_dict(
                row[1:], ["sessions", "messages", "tool_count", "input_tokens", "output_tokens"]
            )
            for row in by_provider
        },
    }


def stats() -> SessionStats:
    """Get unified session statistics."""
    stats_dict = get_stats()

    return SessionStats(
        available=True,
        total_sessions=stats_dict["total_sessions"],
        total_messages=stats_dict["total_messages"],
        total_tools_used=stats_dict["total_tools_used"],
        input_tokens=stats_dict["total_input_tokens"],
        output_tokens=stats_dict["total_output_tokens"],
        by_provider=stats_dict.get("by_provider"),
    )


def resolve_session_id(
    agent_id: str,
    resume: str | None,
    provider: str = "claude",
    identity: str | None = None,
) -> str | None:
    """Resolve resume argument to validated session ID.

    Args:
        agent_id: Agent ID (for spawn lookup if resume is spawn_id)
        resume: Spawn ID, session ID, or short form. Returns None if None.
        provider: Provider name for validation (default: claude)
        identity: Agent identity for CWD validation (optional)

    Returns:
        Validated session ID, or None if:
        - resume is None
        - spawn has no session_id
        - session file doesn't exist
        - no match found

    Raises:
        ValueError: If resume doesn't match any spawn or session

    Note: For @mentions, session continuity uses spawn.session_id from get_active_spawn_in_channel()
    """
    from space.lib import paths
    from space.lib.providers.claude import Claude
    from space.os.spawn import spawns

    def validate_session(session_id: str | None) -> str | None:
        if not session_id:
            return None

        if provider == "claude":
            expected_cwd = str(paths.identity_dir(identity)) if identity else None
            if Claude.session_exists(session_id, expected_cwd):
                return session_id
            logger.debug(f"Session {session_id} not accessible (wrong CWD or deleted)")
            return None

        return session_id

    if not resume:
        return None

    # Try full UUID
    if len(resume) == 36 and resume.count("-") == 4:
        return validate_session(resume)

    # Try spawn lookup (spawn_id → session_id)
    spawn = spawns.get_spawn(resume)
    if spawn and spawn.session_id:
        return validate_session(spawn.session_id)

    # Try short session ID lookup
    try:
        resolved = uuid7.resolve_id("sessions", "id", resume, error_context="resume session")
        return validate_session(resolved)
    except ValueError as e:
        raise ValueError(f"Cannot resolve session or spawn: {e}") from e
