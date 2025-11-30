"""Spawn API endpoints."""

import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator
from pathlib import Path
from queue import Empty, Queue

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

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


@router.get("/{spawn_id}/stream")
async def stream_spawn(spawn_id: str) -> StreamingResponse:
    from space.os.spawn.spawns import get_spawn

    spawn = get_spawn(spawn_id)
    if not spawn:
        raise HTTPException(status_code=404, detail=f"Spawn {spawn_id} not found")

    return StreamingResponse(
        stream_spawn_events(spawn_id, spawn.agent_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


class SessionFileHandler(FileSystemEventHandler):
    def __init__(self, queue: Queue):
        self.queue = queue

    def on_modified(self, event):
        if not event.is_directory:
            self.queue.put("modified")

    def on_created(self, event):
        if not event.is_directory:
            self.queue.put("created")


async def stream_spawn_events(spawn_id: str, agent_id: str) -> AsyncGenerator[str, None]:
    from space.lib import providers
    from space.lib.uuid7 import short_id
    from space.os.spawn import agents

    agent = agents.get_agent_by_id(agent_id)
    if not agent:
        yield f"data: {json.dumps({'type': 'error', 'content': 'Agent not found'})}\n\n"
        return

    marker = short_id(spawn_id)
    provider_class = providers.get_provider(agent.provider)

    session_path: Path | None = None
    sent_count = 0
    queue: Queue = Queue()
    observer: Observer | None = None

    try:
        for _attempt in range(100):
            for search_dir in provider_class.native_session_dirs(None):
                if not search_dir.exists():
                    continue
                session_path = _find_session_by_marker(search_dir, marker, provider_class)
                if session_path:
                    break
            if session_path and session_path.exists():
                break
            await asyncio.sleep(0.2)

        if not session_path or not session_path.exists():
            for _ in range(300):
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)
                for search_dir in provider_class.native_session_dirs(None):
                    if not search_dir.exists():
                        continue
                    session_path = _find_session_by_marker(search_dir, marker, provider_class)
                    if session_path and session_path.exists():
                        break
                if session_path and session_path.exists():
                    break
            if not session_path or not session_path.exists():
                return

        handler = SessionFileHandler(queue)
        observer = Observer()
        observer.schedule(handler, str(session_path.parent), recursive=False)
        observer.start()

        for _ in range(600):
            if not session_path.exists():
                await asyncio.sleep(0.1)
                continue

            messages = provider_class.parse(session_path)
            new_messages = messages[sent_count:]
            if new_messages:
                for msg in new_messages:
                    event_data = {
                        "type": msg.type,
                        "timestamp": msg.timestamp,
                        "content": msg.content,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                sent_count = len(messages)

            with contextlib.suppress(Empty):
                queue.get(timeout=0.1)

            await asyncio.sleep(0.1)

    finally:
        if observer:
            observer.stop()
            observer.join()


def _find_session_by_marker(search_dir: Path, marker: str, provider_class) -> Path | None:
    file_pattern = getattr(provider_class, "SESSION_FILE_PATTERN", "*.jsonl")
    for session_file in search_dir.rglob(file_pattern):
        found_marker = provider_class.parse_spawn_marker(session_file)
        if found_marker == marker:
            return session_file
    return None
