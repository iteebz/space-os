"""Gemini provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.models import AgentMessage, SessionEvent, ToolCall, ToolResult
from space.core.protocols import Provider

logger = logging.getLogger(__name__)


class Gemini(Provider):
    """Gemini provider: chat discovery and message parsing."""

    TMP_DIR = Path.home() / ".gemini" / "tmp"

    @staticmethod
    def allowed_tools() -> list[str]:
        """Return allowed tools for Gemini."""
        return [
            "Edit",
            "FindFiles",
            "GoogleSearch",
            "ReadFile",
            "ReadFolder",
            "ReadManyFiles",
            "SearchText",
            "Shell",
            "WebFetch",
            "WriteFile",
        ]

    @staticmethod
    def launch_args(has_prompt: bool = False) -> list[str]:
        """Return launch arguments for Gemini."""
        allowed = Gemini.allowed_tools()
        args = ["--allowed-tools"] + allowed
        if has_prompt:
            args.append("--prompt-interactive")
        return args

    @staticmethod
    def task_launch_args() -> list[str]:
        """Return launch arguments for task-based Gemini execution.

        Task mode uses stream-json output format, returns JSONL with session_id in first event.
        """
        allowed = Gemini.allowed_tools()
        return ["--output-format", "stream-json", "--allowed-tools"] + allowed

    @staticmethod
    def discover_sessions() -> list[dict]:
        """Discover Gemini sessions from actual chat files and logs.json index."""
        sessions = []
        if not Gemini.TMP_DIR.exists():
            return sessions

        for project_dir in Gemini.TMP_DIR.iterdir():
            if not project_dir.is_dir():
                continue

            project_hash = project_dir.name
            chats_dir = project_dir / "chats"
            logs_file = project_dir / "logs.json"

            # Index sessions from logs.json (fast, metadata only)
            session_metadata = {}
            if logs_file.exists():
                try:
                    with open(logs_file) as f:
                        logs = json.load(f)
                    # Dedupe by sessionId (logs.json has one entry per message)
                    for entry in logs:
                        sid = entry.get("sessionId")
                        if sid and sid not in session_metadata:
                            session_metadata[sid] = {
                                "timestamp": entry.get("timestamp"),
                                "first_message": entry.get("message", ""),
                            }
                except (OSError, json.JSONDecodeError, MemoryError) as e:
                    logger.error(f"Error processing logs.json for project {project_hash}: {e}")

            # Discover actual chat files (ground truth)
            if chats_dir.exists():
                for chat_file in chats_dir.glob("session-*.json"):
                    file_size = chat_file.stat().st_size

                    try:
                        with open(chat_file) as f:
                            chat_data = json.load(f)
                        session_id = chat_data.get("sessionId")
                        if not session_id:
                            continue

                        sessions.append(
                            {
                                "cli": "gemini",
                                "session_id": session_id,
                                "file_path": str(chat_file),
                                "project_hash": project_hash,
                                "created_at": chat_file.stat().st_ctime,
                                "start_time": chat_data.get("startTime"),
                                "last_updated": chat_data.get("lastUpdated"),
                                "message_count": len(chat_data.get("messages", [])),
                                "file_size": file_size,
                                "first_message": session_metadata.get(session_id, {}).get(
                                    "first_message", ""
                                ),
                            }
                        )
                    except (OSError, json.JSONDecodeError, MemoryError) as e:
                        logger.error(f"Error parsing Gemini chat file {chat_file}: {e}")
                        continue

        return sessions

    @staticmethod
    def parse_messages(file_path: Path, from_offset: int = 0) -> list[dict]:
        """
        Parse messages from Gemini JSON or JSONL.

        Handles both:
        - Raw JSON format from provider (single JSON object with messages array)
        - JSONL format from vault (one JSON object per line)
        from_offset is byte offset (like Claude/Codex).
        """
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                content = f.read().decode("utf-8")

            if content.strip().startswith("[") or content.strip().startswith("{"):
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and "messages" in data:
                        for msg in data.get("messages", []):
                            role = msg.get("role")
                            if role not in ("user", "model"):
                                continue
                            messages.append(
                                {
                                    "message_id": None,
                                    "role": "assistant" if role == "model" else "user",
                                    "content": msg.get("content", ""),
                                    "timestamp": msg.get("timestamp"),
                                    "byte_offset": 0,
                                }
                            )
                        return messages
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing Gemini JSON content from {file_path}: {e}")

            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    role = data.get("role")
                    if role not in ("user", "assistant"):
                        continue

                    messages.append(
                        {
                            "message_id": None,
                            "role": role,
                            "content": data.get("content", ""),
                            "timestamp": data.get("timestamp"),
                            "byte_offset": offset,
                        }
                    )
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Gemini messages from {file_path}: {e}")
        return messages

    @staticmethod
    def extract_tokens(file_path: Path) -> tuple[int | None, int | None]:
        """Extract input and output tokens from Gemini JSON (raw format).

        Gemini stores tokens in gemini message objects under tokens.{input,output}
        Extracts from raw JSON before JSONL conversion.
        """
        input_total = 0
        output_total = 0
        found_any = False
        try:
            with open(file_path) as f:
                data = json.load(f)

            if isinstance(data, dict) and "messages" in data:
                for msg in data.get("messages", []):
                    if msg.get("type") == "gemini" and "tokens" in msg:
                        tokens = msg["tokens"]
                        inp = tokens.get("input", 0)
                        out = tokens.get("output", 0)
                        if inp or out:
                            input_total += inp
                            output_total += out
                            found_any = True
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error extracting Gemini tokens from {file_path}: {e}")
        return (input_total if found_any else None, output_total if found_any else None)

    @staticmethod
    def session_id(output: str) -> str | None:
        """Extract session_id from Gemini execution output.

        Gemini returns JSONL stream with first event type=init containing session_id.
        """
        try:
            lines = output.strip().split("\n")
            if not lines:
                return None
            first_line = lines[0]
            data = json.loads(first_line)
            if isinstance(data, dict) and data.get("type") == "init":
                return data.get("session_id")
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.error(f"Failed to parse Gemini headless output: {e}")
        return None

    @staticmethod
    def parse_jsonl(file_path: Path | str) -> list[SessionEvent]:
        """Parse Gemini session JSONL to unified event format.

        Args:
            file_path: Path to Gemini session JSONL

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

                    if msg_type == "model":
                        events.extend(Gemini._parse_model_message(obj.get("parts", []), timestamp))
                    elif msg_type == "user":
                        events.extend(Gemini._parse_user_message(obj.get("parts", []), timestamp))

        except OSError:
            pass

        return events

    @staticmethod
    def _parse_model_message(parts: list, timestamp: str | None) -> list[SessionEvent]:
        """Extract function calls and text from model message."""
        events = []

        for part in parts:
            if isinstance(part, dict):
                if "text" in part:
                    text = AgentMessage(
                        content=part.get("text", ""),
                        timestamp=timestamp,
                    )
                    events.append(SessionEvent(type="text", timestamp=timestamp, data=text))

                elif "functionCall" in part:
                    fn_call = part.get("functionCall", {})
                    tool_call = ToolCall(
                        tool_id=fn_call.get("name", ""),
                        tool_name=fn_call.get("name", ""),
                        input=fn_call.get("args", {}),
                        timestamp=timestamp,
                    )
                    events.append(
                        SessionEvent(type="tool_call", timestamp=timestamp, data=tool_call)
                    )

        return events

    @staticmethod
    def _parse_user_message(parts: list, timestamp: str | None) -> list[SessionEvent]:
        """Extract function results from user message."""
        events = []

        for part in parts:
            if isinstance(part, dict) and "functionResult" in part:
                fn_result = part.get("functionResult", {})
                result_data = fn_result.get("response", {})
                result = ToolResult(
                    tool_id=fn_result.get("name", ""),
                    output=result_data.get("result", "")
                    if isinstance(result_data, dict)
                    else str(result_data),
                    is_error=False,
                    timestamp=timestamp,
                )
                events.append(SessionEvent(type="tool_result", timestamp=timestamp, data=result))

        return events

    def json_to_jsonl(self, json_file: Path) -> str:
        """Convert Gemini JSON session to JSONL format.

        Gemini stores sessions as JSON, but space-os uses JSONL uniformly.

        Args:
            json_file: Path to Gemini JSON session file

        Returns:
            JSONL string (one JSON object per line)
        """
        try:
            with open(json_file) as f:
                data = json.load(f)

            lines = []
            if isinstance(data, dict) and "messages" in data:
                for msg in data.get("messages", []):
                    role = msg.get("role")
                    if role not in ("user", "model"):
                        continue
                    lines.append(
                        json.dumps(
                            {
                                "role": "assistant" if role == "model" else "user",
                                "content": msg.get("content", ""),
                                "timestamp": msg.get("timestamp"),
                            }
                        )
                    )
            return "\n".join(lines) + "\n" if lines else ""
        except (OSError, json.JSONDecodeError):
            return ""
