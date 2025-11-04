"""Codex provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.models import AgentMessage, SessionEvent, ToolCall, ToolResult
from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Codex(Provider):
    """Codex provider: chat discovery and message parsing.

    Codex supports two models: gpt-5-codex (optimized for coding) and gpt-5 (general).
    Reasoning effort defaults to low and is configured via codex config, not CLI args.
    """

    SESSIONS_DIR = Path.home() / ".codex" / "sessions"

    @staticmethod
    def launch_args() -> list[str]:
        """Return launch arguments for Codex."""
        return ["--dangerously-bypass-approvals-and-sandbox"]

    @staticmethod
    def task_launch_args() -> list[str]:
        """Return launch arguments for task-based Codex execution.

        Task mode uses --json flag, returns JSONL with thread_id in first event.
        """
        return ["--json", "--dangerously-bypass-approvals-and-sandbox"]

    @staticmethod
    def discover_sessions() -> list[dict]:
        """Discover Codex sessions."""
        sessions = []
        if not Codex.SESSIONS_DIR.exists():
            return sessions

        for jsonl in Codex.SESSIONS_DIR.rglob("*.jsonl"):
            sessions.append(
                {
                    "cli": "codex",
                    "session_id": jsonl.stem,
                    "file_path": str(jsonl),
                    "created_at": jsonl.stat().st_ctime,
                }
            )
        return sessions

    @staticmethod
    def parse_messages(file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from Codex JSONL."""
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    msg_type = data.get("type")
                    payload = data.get("payload", {})

                    if msg_type == "response_item":
                        role = payload.get("role")
                        if role not in ("user", "assistant"):
                            continue

                        content_list = payload.get("content", [])
                        content = ""
                        if isinstance(content_list, list):
                            content = "\n".join(
                                item.get("text", "")
                                for item in content_list
                                if isinstance(item, dict) and item.get("type") == "input_text"
                            )

                        else:
                            content = content_list

                        msg = {
                            "message_id": payload.get("id"),
                            "role": role,
                            "content": content,
                            "timestamp": data.get("timestamp"),
                            "cwd": payload.get("cwd"),
                            "byte_offset": offset,
                        }
                        messages.append(msg)
                    elif msg_type in ("tool_call", "tool_result"):
                        content_list = payload.get("content", [])
                        content = ""
                        if isinstance(content_list, list):
                            content = "\n".join(
                                item.get("text", "")
                                for item in content_list
                                if isinstance(item, dict) and item.get("type") == "input_text"
                            )
                        else:
                            content = content_list

                        msg = {
                            "message_id": payload.get("id"),
                            "role": "tool",
                            "content": content,
                            "timestamp": data.get("timestamp"),
                            "cwd": payload.get("cwd"),
                            "tool_type": msg_type,
                            "byte_offset": offset,
                        }
                        messages.append(msg)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Codex messages from {file_path}: {e}")
        return messages

    @staticmethod
    def extract_tokens(file_path: Path) -> tuple[int | None, int | None]:
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
    def session_id(output: str) -> str | None:
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
    def parse_jsonl(file_path: Path | str) -> list[SessionEvent]:
        """Parse Codex session JSONL to unified event format.

        Args:
            file_path: Path to Codex session JSONL

        Returns:
            List of Event objects in chronological order
        """
        file_path = Path(file_path)
        events = []

        if not file_path.exists():
            return events

        try:
            with open(file_path) as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    role = obj.get("role")
                    timestamp = obj.get("timestamp")

                    if role == "assistant":
                        events.extend(Codex._parse_assistant_message(obj, timestamp))
                    elif role == "tool":
                        events.extend(Codex._parse_tool_result_message(obj, timestamp))

        except OSError:
            pass

        return events

    @staticmethod
    def _parse_assistant_message(message: dict, timestamp: str | None) -> list[SessionEvent]:
        """Extract tool calls and text from assistant message."""
        events = []
        content = message.get("content")

        if content:
            text = AgentMessage(
                content=content,
                timestamp=timestamp,
            )
            events.append(SessionEvent(type="text", timestamp=timestamp, data=text))

        tool_calls = message.get("tool_calls", [])
        for tool_call_obj in tool_calls:
            if isinstance(tool_call_obj, dict):
                fn = tool_call_obj.get("function", {})
                arguments = fn.get("arguments", "")

                try:
                    parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
                except json.JSONDecodeError:
                    parsed_args = {"raw": arguments}

                tool_call = ToolCall(
                    tool_id=tool_call_obj.get("id", ""),
                    tool_name=fn.get("name", ""),
                    input=parsed_args,
                    timestamp=timestamp,
                )
                events.append(SessionEvent(type="tool_call", timestamp=timestamp, data=tool_call))

        return events

    @staticmethod
    def _parse_tool_result_message(message: dict, timestamp: str | None) -> list[SessionEvent]:
        """Extract tool result from tool message."""
        events = []

        result = ToolResult(
            tool_id=message.get("tool_call_id", ""),
            output=message.get("content", ""),
            is_error=False,
            timestamp=timestamp,
        )
        events.append(SessionEvent(type="tool_result", timestamp=timestamp, data=result))

        return events
