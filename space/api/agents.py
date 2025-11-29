"""Agent API endpoints."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def get_agents():
    from space.lib import store

    try:
        with store.ensure() as conn:
            rows = conn.execute(
                """SELECT agent_id, identity, model, constitution, role, spawn_count,
                          created_at, last_active_at, archived_at
                   FROM agents
                   WHERE archived_at IS NULL
                   ORDER BY constitution, identity"""
            ).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{identity}/memories")
def get_agent_memories(identity: str, topic: str | None = None, limit: int = 50):
    from dataclasses import asdict

    from space.os.memory import operations as memory

    try:
        memories = memory.list_memories(identity, topic=topic, limit=limit)
        return [asdict(m) for m in memories]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{agent_id}/sessions")
def get_agent_sessions(agent_id: str):
    from space.lib import store

    with store.ensure() as conn:
        rows = conn.execute(
            """
            SELECT session_id, provider, model, first_message_at, last_message_at
            FROM sessions
            WHERE agent_id = ?
            ORDER BY last_message_at DESC
            """,
            (agent_id,),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No sessions for agent {agent_id}")

    return [
        {
            "session_id": row[0],
            "provider": row[1],
            "model": row[2],
            "first_message_at": row[3],
            "last_message_at": row[4],
        }
        for row in rows
    ]
