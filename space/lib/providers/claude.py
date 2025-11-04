"""Claude provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.models import AgentMessage, SessionEvent, ToolCall, ToolResult
from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Claude(Provider):
    """Claude provider: chat discovery and message parsing."""

    SESSIONS_DIR = Path.home() / ".claude" / "projects"

    @staticmethod
    def allowed_tools() -> list[str]:
        """Return allowed tools for Claude."""
        return [
            "Bash",
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Grep",
            "Glob",
            "WebSearch",
            "WebFetch",
            "LS",
        ]

    @staticmethod
    def launch_args(is_task: bool = False) -> list[str]:
        """Return launch arguments for Claude.

        Args:
            is_task: Whether this is a task-based spawn. Only task spawns skip permissions.
        """
        disallowed = [
            "NotebookRead",
            "NotebookEdit",
            "Task",
            "TodoWrite",
        ]
        args = ["--disallowedTools", ",".join(disallowed)]
        if is_task:
            args.insert(0, "--dangerously-skip-permissions")
        return args

    @staticmethod
    def task_launch_args() -> list[str]:
        """Return launch arguments for task-based Claude execution.

        Task mode uses stdin input and JSON output format.
        """
        disallowed = [
            "NotebookRead",
            "NotebookEdit",
            "Task",
            "TodoWrite",
        ]
        return [
            "--dangerously-skip-permissions",
            "--output-format",
            "json",
            "--disallowedTools",
            ",".join(disallowed),
        ]

    @staticmethod
    def discover_sessions() -> list[dict]:
        """Discover Claude sessions."""
        sessions = []
        if not Claude.SESSIONS_DIR.exists():
            return sessions

        for jsonl in Claude.SESSIONS_DIR.rglob("*.jsonl"):
            sessions.append(
                {
                    "cli": "claude",
                    "session_id": jsonl.stem,
                    "file_path": str(jsonl),
                    "created_at": jsonl.stat().st_ctime,
                }
            )
        return sessions

    @staticmethod
    def parse_messages(file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from Claude JSONL."""
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    role = data.get("type")
                    if role not in ("user", "assistant", "tool"):
                        continue
                    message_obj = data.get("message", {})
                    content = ""
                    if isinstance(message_obj, dict):
                        content_raw = message_obj.get("content", "")
                        if isinstance(content_raw, list):
                            content = "\n".join(
                                item.get("text", "")
                                for item in content_raw
                                if isinstance(item, dict) and item.get("type") == "text"
                            )
                        else:
                            content = content_raw
                    else:
                        content = message_obj

                    msg = {
                        "message_id": data.get("uuid"),
                        "role": role,
                        "content": content,
                        "timestamp": data.get("timestamp"),
                        "cwd": data.get("cwd"),
                        "byte_offset": offset,
                    }
                    if role == "tool":
                        msg["tool_type"] = "tool_result"
                    messages.append(msg)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Claude messages from {file_path}: {e}")
        return messages

    @staticmethod
    def extract_tokens(file_path: Path) -> tuple[int | None, int | None]:
        """Extract input and output tokens from Claude JSONL.

        Claude stores tokens in message.usage.{input,output}_tokens
        """
        input_total = 0
        output_total = 0
        found_any = False
        try:
            with open(file_path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "message" in obj:
                            msg = obj["message"]
                            if isinstance(msg, dict) and "usage" in msg:
                                usage = msg["usage"]
                                inp = usage.get("input_tokens", 0)
                                out = usage.get("output_tokens", 0)
                                if inp or out:
                                    input_total += inp
                                    output_total += out
                                    found_any = True
                    except json.JSONDecodeError:
                        continue
        except OSError as e:
            logger.error(f"Error extracting Claude tokens from {file_path}: {e}")
        return (input_total if found_any else None, output_total if found_any else None)

    @staticmethod
    def session_id(output: str) -> str | None:
        """Extract session_id from Claude execution output.

        Claude returns a JSON object with session_id at root level.
        """
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                return data.get("session_id")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Claude headless output: {e}")
        return None

    @staticmethod
    def parse_jsonl(file_path: Path | str) -> list[SessionEvent]:
        """Parse Claude session JSONL to unified event format.

        Args:
            file_path: Path to Claude session JSONL

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

                    msg_type = obj.get("type")
                    timestamp = obj.get("timestamp")

                    if msg_type == "assistant":
                        events.extend(
                            Claude._parse_assistant_message(obj.get("message", {}), timestamp)
                        )
                    elif msg_type == "user":
                        events.extend(Claude._parse_user_message(obj.get("message", {}), timestamp))

        except OSError:
            pass

        return events

    @staticmethod
    def _parse_assistant_message(message: dict, timestamp: str | None) -> list[SessionEvent]:
        """Extract tool calls and text from assistant message."""
        events = []
        content = message.get("content", [])

        for item in content:
            item_type = item.get("type")

            if item_type == "tool_use":
                tool_call = ToolCall(
                    tool_id=item.get("id", ""),
                    tool_name=item.get("name", ""),
                    input=item.get("input", {}),
                    timestamp=timestamp,
                )
                events.append(SessionEvent(type="tool_call", timestamp=timestamp, data=tool_call))

            elif item_type == "text":
                text = AgentMessage(
                    content=item.get("text", ""),
                    timestamp=timestamp,
                )
                events.append(SessionEvent(type="text", timestamp=timestamp, data=text))

        return events

    @staticmethod
    def _parse_user_message(message: dict, timestamp: str | None) -> list[SessionEvent]:
        """Extract tool results from user message."""
        events = []
        content = message.get("content", [])

        for item in content:
            item_type = item.get("type")

            if item_type == "tool_result":
                result = ToolResult(
                    tool_id=item.get("tool_use_id", ""),
                    output=item.get("content", ""),
                    is_error=item.get("is_error", False),
                    timestamp=timestamp,
                )
                events.append(SessionEvent(type="tool_result", timestamp=timestamp, data=result))

        return events
