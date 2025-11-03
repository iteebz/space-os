"""Agent trace: recent spawns and execution history."""

from space.core import db
from space.lib.ids import truncate_uuid


def trace_agent(identity: str, limit: int = 10) -> dict:
    """Get execution trace for agent: recent spawns with outcomes.

    Args:
        identity: Agent identity name
        limit: Number of recent spawns to return

    Returns:
        Dict with agent info and recent spawn sequence
    """
    db.register()

    with db.connect() as conn:
        agent_row = conn.execute(
            "SELECT agent_id FROM agents WHERE identity = ?", (identity,)
        ).fetchone()

    if not agent_row:
        raise ValueError(f"Agent '{identity}' not found")

    agent_id = agent_row[0]

    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT session_id, agent_id, status, started_at, ended_at,
                   input, output, stderr, chat_id
            FROM sessions
            WHERE agent_id = ?
            ORDER BY started_at DESC LIMIT ?
            """,
            (agent_id, limit),
        ).fetchall()

    spawns = []
    for row in rows:
        session_id = row[0]
        short_id = truncate_uuid(session_id)
        status = row[2]
        started_at = row[3]
        ended_at = row[4]
        output = row[6]
        stderr = row[7]

        duration = None
        if started_at and ended_at:
            from datetime import datetime

            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(ended_at)
            duration = (end - start).total_seconds()

        outcome_text = ""
        if status == "COMPLETED" and output:
            outcome_text = output[:80].replace("\n", " ")
        elif status == "FAILED" and stderr:
            outcome_text = f"ERROR: {stderr[:80].replace(chr(10), ' ')}"
        elif status == "FAILED":
            outcome_text = "ERROR: (no stderr captured)"

        spawns.append(
            {
                "session_id": session_id,
                "short_id": short_id,
                "status": status,
                "started_at": started_at,
                "duration_seconds": duration,
                "outcome": outcome_text,
            }
        )

    return {
        "type": "identity",
        "identity": identity,
        "agent_id": agent_id,
        "recent_spawns": spawns,
    }
