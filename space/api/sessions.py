"""Session API endpoints."""

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

from space.lib import paths

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionFileHandler(FileSystemEventHandler):
    def __init__(self, queue: Queue):
        self.queue = queue

    def on_modified(self, event):
        if not event.is_directory:
            self.queue.put("modified")


@router.get("/{session_id}/last-tool")
async def get_last_tool(session_id: str) -> dict:
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

    provider_class = providers.get_provider(provider_name)
    messages = provider_class.parse(session_path)

    for msg in reversed(messages):
        if msg.type == "tool_call":
            content = msg.content
            if isinstance(content, dict) and "input" in content:
                tool_input = content["input"]
                if isinstance(tool_input, dict) and "description" in tool_input:
                    return {
                        "description": tool_input["description"],
                        "timestamp": msg.timestamp,
                    }

    return {"description": None, "timestamp": None}


@router.get("/{session_id}/stream")
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
