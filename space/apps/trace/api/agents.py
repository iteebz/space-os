"""Agent trace: recent spawns and execution history."""

from datetime import datetime

from space.lib.ids import truncate_uuid
from space.os import spawn


def trace_agent(identity: str, limit: int = 10) -> dict:
    """Get execution trace for agent: recent spawns with outcomes.

    Args:
        identity: Agent identity name
        limit: Number of recent spawns to return

    Returns:
        Dict with agent info and recent spawn sequence
    """
    agent = spawn.get_agent(identity)
    if not agent:
        raise ValueError(f"Agent '{identity}' not found")

    agent_id = agent.agent_id
    sessions = spawn.get_sessions_for_agent(agent_id, limit=limit)

    spawns = []
    for session in sessions:
        short_id = truncate_uuid(session.id)
        status = session.status
        started_at = session.created_at
        ended_at = session.ended_at
        output = session.output
        stderr = session.stderr

        duration = None
        if started_at and ended_at:
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
                "session_id": session.id,
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
