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


MODEL_CONTEXT_LIMITS = {
    "claude-opus-4": 200000,
    "claude-sonnet-4": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    "claude-haiku-4": 200000,
    "default": 200000,
}


def _get_model_limit(model: str) -> int:
    for prefix, limit in MODEL_CONTEXT_LIMITS.items():
        if model.startswith(prefix):
            return limit
    return MODEL_CONTEXT_LIMITS["default"]


@router.get("/{session_id}/usage")
async def get_session_usage(session_id: str) -> dict:
    import json as json_lib

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

    input_tokens = 0
    output_tokens = 0
    model = "unknown"

    with open(session_path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json_lib.loads(line)
                if isinstance(obj, dict) and "message" in obj:
                    msg = obj["message"]
                    if isinstance(msg, dict):
                        if "model" in msg and not model.startswith("claude"):
                            model = msg["model"]
                        if "usage" in msg:
                            stop_reason = msg.get("stop_reason")
                            if stop_reason in ("end_turn", "tool_use"):
                                usage = msg["usage"]
                                input_tokens = usage.get("input_tokens", 0)
                                input_tokens += usage.get("cache_read_input_tokens", 0)
                                input_tokens += usage.get("cache_creation_input_tokens", 0)
                                output_tokens = usage.get("output_tokens", 0)
            except json_lib.JSONDecodeError:
                continue

    context_limit = _get_model_limit(model)
    context_used = input_tokens + output_tokens
    percentage = min(100, (context_used / context_limit) * 100) if context_limit > 0 else 0

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "context_used": context_used,
        "context_limit": context_limit,
        "percentage": round(percentage, 1),
        "model": model,
    }


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

        provider_class = providers.get_provider(provider)
        for native_dir in provider_class.native_session_dirs(None):
            candidate = native_dir / f"{session_id}.jsonl"
            if candidate.exists():
                session_path = candidate
                provider_name = provider
                break
        if session_path:
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
