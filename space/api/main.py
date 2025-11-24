"""FastAPI wrapper for Space-OS APIs."""

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from queue import Empty, Queue

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from space.lib import paths

app = FastAPI(title="Space API")
START_TIME = time.time()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SendMessage(BaseModel):
    content: str
    sender: str = "human"


class CreateChannel(BaseModel):
    name: str
    topic: str | None = None


class UpdateTopic(BaseModel):
    topic: str


class SessionFileHandler(FileSystemEventHandler):
    def __init__(self, queue: Queue):
        self.queue = queue

    def on_modified(self, event):
        if not event.is_directory:
            self.queue.put("modified")


@app.get("/api/channels")
async def get_channels():
    from dataclasses import asdict

    from space.os.bridge.api import channels

    try:
        channels_list = channels.list_channels(show_all=False)
        return [asdict(ch) for ch in channels_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/channels")
async def create_channel(body: CreateChannel):
    from space.os.bridge.api import channels

    try:
        channel = channels.create_channel(body.name, body.topic)
        return {"ok": True, "name": channel.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/channels/{channel}/messages")
async def get_messages(channel: str):
    from dataclasses import asdict

    from space.os.bridge.api import messaging

    try:
        messages, _, _, _ = messaging.recv_messages(channel)
        return [asdict(msg) for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.patch("/api/channels/{channel}/topic")
async def update_channel_topic(channel: str, body: UpdateTopic):
    from space.os.bridge.api import channels

    try:
        success = channels.update_topic(channel, body.topic)
        if not success:
            raise HTTPException(status_code=404, detail=f"Channel {channel} not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/api/channels/{channel}")
async def delete_channel(channel: str):
    from space.os.bridge.api import channels

    try:
        channels.delete_channel(channel)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/channels/{channel}/archive")
async def archive_channel(channel: str):
    from space.os.bridge.api import channels

    try:
        channels.archive_channel(channel)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/spawns")
async def get_spawns():
    from dataclasses import asdict

    from space.os.spawn.api import spawns

    try:
        spawns_list = spawns.get_all_spawns(limit=100)
        return [asdict(sp) for sp in spawns_list]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/agents")
async def get_agents():
    from space.os.spawn.api import agents

    try:
        mapping = agents.agent_identities()
        return [{"agent_id": aid, "identity": identity} for aid, identity in mapping.items()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/health")
def health_check():
    from space.lib import store

    uptime_seconds = int(time.time() - START_TIME)
    db_ok = False
    db_error = None

    try:
        with store.ensure() as conn:
            conn.execute("SELECT 1").fetchone()
        db_ok = True
    except Exception as e:
        db_error = str(e)

    return {
        "uptime_seconds": uptime_seconds,
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
    }


@app.get("/api/agents/{agent_id}/sessions")
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


@app.get("/api/channels/{channel_name}/agents/{agent_identity}/sessions")
def get_channel_agent_sessions(channel_name: str, agent_identity: str):
    from space.lib import store
    from space.os.bridge.api import channels
    from space.os.spawn.api import agents

    channel = channels.get_channel(channel_name)
    if not channel:
        raise HTTPException(status_code=404, detail=f"Channel {channel_name} not found")

    agent = agents.get_agent(agent_identity)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_identity} not found")

    with store.ensure() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT s.session_id, s.provider, s.model, s.first_message_at, s.last_message_at
            FROM sessions s
            JOIN spawns sp ON s.session_id = sp.session_id
            WHERE sp.channel_id = ? AND sp.agent_id = ?
            ORDER BY s.last_message_at DESC
            """,
            (channel.channel_id, agent.agent_id),
        ).fetchall()

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


@app.get("/api/spawns/{spawn_id}/tree")
def get_spawn_tree(spawn_id: str):
    from space.lib import store
    from space.os.spawn.api.spawns import get_spawn

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


@app.post("/api/channels/{channel}/messages")
async def send_message(channel: str, body: SendMessage):
    from space.os.bridge.api import messaging

    try:
        message_id = await messaging.send_message(channel, body.sender, body.content)
        return {"ok": True, "message_id": message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/api/messages/{message_id}")
async def delete_message(message_id: str):
    from space.os.bridge.api import messaging

    try:
        deleted = messaging.delete_message(message_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/sessions/{session_id}/stream")
async def stream_session(session_id: str) -> StreamingResponse:
    from space.lib import providers

    sessions_dir = paths.sessions_dir()
    session_path = None
    provider_name = None

    for provider in providers.PROVIDER_NAMES:
        candidate = sessions_dir / provider / f"{session_id}.jsonl"
        if candidate.exists():
            session_path = candidate
            provider_name = provider
            break

    if not session_path or not provider_name:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return StreamingResponse(
        stream_session_events(session_path, provider_name),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def stream_session_events(
    session_path: Path, provider_name: str
) -> AsyncGenerator[str, None]:
    from space.lib import providers

    queue: Queue = Queue()
    handler = SessionFileHandler(queue)
    observer = Observer()
    observer.schedule(handler, str(session_path.parent), recursive=False)
    observer.start()

    provider_class = providers.get_provider(provider_name)
    sent_count = 0
    try:
        while True:
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
        observer.stop()
        observer.join()


def main():
    import uvicorn

    uvicorn.run("space.api.main:app", host="0.0.0.0", port=8000, access_log=False, reload=True)


if __name__ == "__main__":
    main()
