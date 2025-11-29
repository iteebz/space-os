"""Spawn API endpoints."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/spawns", tags=["spawns"])


@router.get("")
async def get_spawns():
    from dataclasses import asdict

    from space.os.spawn import spawns

    try:
        spawns_list = spawns.get_all_spawns(limit=100)
        return [asdict(sp) for sp in spawns_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{spawn_id}/tree")
def get_spawn_tree(spawn_id: str):
    from space.lib import store
    from space.os.spawn.spawns import get_spawn

    spawn = get_spawn(spawn_id)
    if not spawn:
        raise HTTPException(status_code=404, detail=f"Spawn {spawn_id} not found")

    with store.ensure() as conn:
        descendants = conn.execute(
            """
            WITH RECURSIVE spawn_tree AS (
                SELECT id, agent_id, parent_spawn_id, status, created_at, ended_at
                FROM spawns
                WHERE id = ?
                UNION ALL
                SELECT s.id, s.agent_id, s.parent_spawn_id, s.status, s.created_at, s.ended_at
                FROM spawns s
                INNER JOIN spawn_tree st ON s.parent_spawn_id = st.id
            )
            SELECT * FROM spawn_tree
            """,
            (spawn_id,),
        ).fetchall()

    return {
        "spawn_id": spawn.id,
        "agent_id": spawn.agent_id,
        "status": spawn.status,
        "created_at": spawn.created_at,
        "ended_at": spawn.ended_at,
        "descendants": [
            {
                "id": row[0],
                "agent_id": row[1],
                "parent_spawn_id": row[2],
                "status": row[3],
                "created_at": row[4],
                "ended_at": row[5],
            }
            for row in descendants
        ],
    }
