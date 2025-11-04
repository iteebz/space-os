"""Session operations: search and statistics."""

import logging

from space.core.models import SessionStats
from space.lib import store

logger = logging.getLogger(__name__)


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[dict]:
    """Search transcripts via FTS5 (implicit episodic memory).

    Args:
        query: Search query (supports FTS5 syntax: phrase, boolean, wildcards, NEAR)
        identity: Unused in Phase 1 (reserved for Phase 2 identity filtering)
        all_agents: Unused in Phase 1 (reserved for Phase 2 multi-agent filtering)

    Returns:
        List of results matching the query, sorted by BM25 relevance + recency.
        Each result has: source, cli, session_id, identity, role, text, timestamp, reference, score
    """
    results = []

    try:
        with store.ensure() as conn:
            rows = conn.execute(
                """
                SELECT
                    t.session_id,
                    t.provider,
                    t.role,
                    t.identity,
                    t.content,
                    t.timestamp,
                    fts.rank
                FROM transcripts t
                JOIN transcripts_fts fts ON t.id = fts.rowid
                WHERE fts.transcripts_fts MATCH ?
                ORDER BY fts.rank, t.timestamp DESC
                LIMIT 100
                """,
                (query,),
            ).fetchall()

            for row in rows:
                session_id, provider, role, identity, content, timestamp, rank = row
                score = abs(rank)

                results.append(
                    {
                        "source": "chat",
                        "cli": provider,
                        "session_id": session_id,
                        "role": role,
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
