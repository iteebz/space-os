"""Codex provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.models import SessionMessage
from space.core.protocols import Provider

from . import base

logger = logging.getLogger(__name__)


class Codex(Provider):
    """Codex provider: chat discovery and message parsing.

    Codex supports models with optional reasoning effort suffixes:
    - gpt-5.1-codex, gpt-5.1-codex-mini, gpt-5.1
    - Reasoning: -low, -medium, -high
    """

    SESSIONS_DIR = Path.home() / ".codex" / "sessions"

    @staticmethod
    def parse_model_id(model_id: str) -> tuple[str, str | None]:
        """Parse model ID into (base_model, reasoning_effort).

        Examples:
            'gpt-5.1-codex-low' -> ('gpt-5.1-codex', 'low')
            'gpt-5.1-codex-mini-high' -> ('gpt-5.1-codex-mini', 'high')
            'gpt-5.1' -> ('gpt-5.1', None)
        """
        for effort in ("low", "medium", "high"):
            if model_id.endswith(f"-{effort}"):
                base = model_id[: -(len(effort) + 1)]
                return (base, effort)
        return (model_id, None)

    @staticmethod
    def launch_args(reasoning_effort: str | None = None) -> list[str]:
        """Return launch arguments for Codex."""
        args = ["--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check"]
        if reasoning_effort:
            args.extend(["-c", f"model_reasoning_effort={reasoning_effort}"])
        return args

    @staticmethod
    def task_launch_args(
        reasoning_effort: str | None = None, image_paths: list[str] | None = None
    ) -> list[str]:
        """Return launch arguments for task-based Codex execution.

        Task mode uses --json flag, returns JSONL with thread_id in first event.
        """
        args = ["--json", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check"]
        if reasoning_effort:
            args.extend(["-c", f"model_reasoning_effort={reasoning_effort}"])
        if image_paths:
            for path in image_paths:
                args.extend(["-i", path])
        return args

    @staticmethod
    def discover() -> list[dict]:
        """Discover Codex sessions."""
        sessions = []
        if not Codex.SESSIONS_DIR.exists():
            return sessions

        for jsonl in Codex.SESSIONS_DIR.rglob("*.jsonl"):
            session_id = Codex.session_id_from_contents(jsonl)
            if not session_id:
                continue
            sessions.append(
                {
                    "cli": "codex",
                    "session_id": session_id,
                    "file_path": str(jsonl),
                    "created_at": jsonl.stat().st_ctime,
                }
            )
        return sessions

    @staticmethod
    def ingest(session: dict, dest_dir: Path) -> bool:
        """Ingest one Codex session: copy to destination with normalized filename.

        Extracts canonical session_id (thread_id) from file to normalize filename to {uuid}.jsonl.
        """
        return base.ingest_session_copy(session, dest_dir, "codex", Codex.session_id_from_contents)

    @staticmethod
    def index(session_id: str) -> int:
        """Index one Codex session into database."""
        return base.index_session(session_id, "codex")

    @staticmethod
    def parse(file_path: Path | str, from_offset: int = 0) -> list[SessionMessage]:
        """Parse Codex session data to unified event format.

        Accepts file path or raw JSONL string content.
        """

        def parse_line(obj: dict, line_num: int) -> list[SessionMessage]:
            events = []
            role = obj.get("role")
            timestamp = obj.get("timestamp")

            if role == "assistant":
                events.extend(Codex._parse_assistant_message(obj, timestamp))
            elif role == "tool":
                events.extend(Codex._parse_tool_result_message(obj, timestamp))

            payload = obj.get("payload", {})
            if payload.get("type") == "message":
                payload_role = payload.get("role", "").lower()
                if payload_role in ("user", "assistant"):
                    text = Codex._extract_payload_text(payload)
                    if text:
                        events.append(
                            SessionMessage(
                                type="message",
                                timestamp=timestamp,
                                content={"role": payload_role, "text": text},
                            )
                        )

            return events

        return base.parse_jsonl_file(file_path, parse_line, from_offset)

    @staticmethod
    def tokens(file_path: Path) -> tuple[int | None, int | None]:
        """Extract input and output tokens from Codex JSONL.

        Codex stores tokens in token_count events under info.total_token_usage
        Returns the most recent token counts found.
        """
        input_tokens = None
        output_tokens = None
        try:
            with open(file_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "payload" in obj:
                            payload = obj["payload"]
                            if payload.get("type") == "token_count" and "info" in payload:
                                info = payload["info"]
                                if isinstance(info, dict) and "total_token_usage" in info:
                                    usage = info["total_token_usage"]
                                    input_tokens = usage.get("input_tokens")
                                    output_tokens = usage.get("output_tokens")
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.error(f"Error extracting Codex tokens from {file_path}: {e}")
        return (input_tokens, output_tokens)

    @staticmethod
    def session_id_from_stream(output: str) -> str | None:
        """Extract session_id (thread_id) from Codex execution output.

        Codex returns JSONL stream with first event type=thread.started containing thread_id.
        """
        try:
            lines = output.strip().split("\n")
            if not lines:
                return None
            first_line = lines[0]
            data = json.loads(first_line)
            if isinstance(data, dict) and data.get("type") == "thread.started":
                return data.get("thread_id")
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.error(f"Failed to parse Codex headless output: {e}")
        return None

    @staticmethod
    def session_id_from_contents(file_path: Path) -> str | None:
        """Extract session_id from Codex JSONL file contents.

        Codex stores session ID in first line's payload.id field (session_meta event).
        """
        try:
            with open(file_path) as f:
                first_line = f.readline()
                if not first_line.strip():
                    return None
                obj = json.loads(first_line)
                if isinstance(obj, dict):
                    payload = obj.get("payload", {})
                    if isinstance(payload, dict):
                        return payload.get("id")
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to extract session_id from {file_path}: {e}")
        return None

    @staticmethod
    def _parse_assistant_message(message: dict, timestamp: str | None) -> list[SessionMessage]:
        """Extract tool calls and text from assistant message."""
        messages = []
        content = message.get("content")

        if content:
            messages.append(SessionMessage(type="text", timestamp=timestamp, content=content))

        tool_calls = message.get("tool_calls", [])
        for tool_call_obj in tool_calls:
            if isinstance(tool_call_obj, dict):
                fn = tool_call_obj.get("function", {})
                arguments = fn.get("arguments", "")

                try:
                    parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                except json.JSONDecodeError:
                    parsed_args = {"raw": arguments}

                messages.append(
                    SessionMessage(
                        type="tool_call",
                        timestamp=timestamp,
                        content={
                            "tool_name": fn.get("name", ""),
                            "input": parsed_args,
                        },
                    )
                )

        return messages

    @staticmethod
    def _extract_payload_text(payload: dict) -> str:
        """Extract text from Codex payload content array."""
        content = payload.get("content", [])
        if not isinstance(content, list):
            return ""

        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in ("input_text", "output_text"):
                texts.append(item.get("text", ""))
        return "\n".join(texts).strip()

    @staticmethod
    def _parse_tool_result_message(message: dict, timestamp: str | None) -> list[SessionMessage]:
        """Extract tool result from tool message."""
        messages = []

        messages.append(
            SessionMessage(
                type="tool_result",
                timestamp=timestamp,
                content={
                    "output": message.get("content", ""),
                    "is_error": False,
                },
            )
        )

        return messages
