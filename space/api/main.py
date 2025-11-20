"""FastAPI wrapper around CLI primitives."""

import asyncio
import contextlib
import json
import subprocess
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
from space.lib.providers import Claude

app = FastAPI(title="Space API")

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


def run_cli(cmd: list[str]) -> dict | list:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response", "raw": result.stdout}


@app.get("/api/channels")
def get_channels():
    return run_cli(["bridge", "--json", "channels"])


@app.post("/api/channels")
def create_channel(body: CreateChannel):
    cmd = ["bridge", "create", body.name]
    if body.topic:
        cmd.extend(["--topic", body.topic])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return {"ok": True, "name": body.name}


@app.get("/api/channels/{channel}/messages")
def get_messages(channel: str):
    return run_cli(["bridge", "recv", channel, "--json"])


@app.patch("/api/channels/{channel}/topic")
def update_topic(channel: str, body: UpdateTopic):
    result = subprocess.run(
        ["bridge", "topic", channel, body.topic],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return {"ok": True}


@app.get("/api/spawns")
def get_spawns():
    return run_cli(["spawn", "--json", "tasks", "--all"])


@app.get("/api/agents")
def get_agents():
    return run_cli(["spawn", "agents", "--json"])


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
def send_message(channel: str, body: SendMessage):
    result = subprocess.run(
        ["bridge", "--as", body.sender, "send", channel, body.content],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip()}
    return {"ok": True}


@app.get("/api/sessions/{session_id}/stream")
async def stream_session(session_id: str) -> StreamingResponse:
    sessions_dir = paths.sessions_dir()
    session_path = None

    for provider in ("claude", "codex", "gemini"):
        candidate = sessions_dir / provider / f"{session_id}.jsonl"
        if candidate.exists():
            session_path = candidate
            break

    if not session_path:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return StreamingResponse(
        stream_session_events(session_path),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def stream_session_events(session_path: Path) -> AsyncGenerator[str, None]:
    queue: Queue = Queue()
    handler = SessionFileHandler(queue)
    observer = Observer()
    observer.schedule(handler, str(session_path.parent), recursive=False)
    observer.start()

    sent_count = 0
    try:
        while True:
            messages = Claude.parse(session_path)
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

    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)


if __name__ == "__main__":
    main()
