"""Gemini provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.models import SessionMessage
from space.core.protocols import Provider

from . import base

logger = logging.getLogger(__name__)


def is_system_bloat(content: str) -> bool:
    """Filter out Gemini's system messages.

    Gemini wraps internal continuation prompts as "System: Please continue."
    These are not user/agent conversation content.
    """
    return content.strip().startswith("System:")


class Gemini(Provider):
    """Gemini provider: chat discovery and message parsing."""

    TMP_DIR = Path.home() / ".gemini" / "tmp"
    SESSIONS_DIR = TMP_DIR
    SESSION_FILE_PATTERN = "*/chats/session-*.json"

    @staticmethod
    def extract_session_id(output: str) -> str | None:
        """Extract session ID from Gemini CLI output.

        Gemini doesn't expose session IDs in stdout like Claude/Codex.
        Returns None - must rely on file discovery.
        """
        return None

    @staticmethod
    def discover_session(spawn, start_ts: float, end_ts: float) -> str | None:
        """Discover Gemini session created during spawn window.

        Strategy: Match by mtime within spawn time window, return closest to start.
        """
        if not Gemini.SESSIONS_DIR.exists():
            return None

        candidates = []

        for session_file in Gemini.SESSIONS_DIR.rglob("session-*.json"):
            try:
                mtime = session_file.stat().st_mtime
                if start_ts <= mtime <= end_ts:
                    session_id = session_file.stem.replace("session-", "")
                    candidates.append((session_id, abs(mtime - start_ts)))
            except OSError:
                continue

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

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
        """Return launch arguments for task-based Gemini execution."""
        allowed = Gemini.allowed_tools()
        return ["--yolo", "--allowed-tools"] + allowed

    @staticmethod
    def discover() -> list[dict]:
        """Discover Gemini sessions from actual chat files and logs.json index.

        Note: Gemini reuses sessionIds across different conversations.
        We use file stem (filename without extension) as unique key instead.
        """
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
                        gemini_session_id = chat_data.get("sessionId")
                        if not gemini_session_id:
                            continue

                        # Use filename as unique session_id (handles Gemini's sessionId reuse bug)
                        # Filename format: session-YYYY-MM-DDTHH-MM-{gemini_session_id}.json
                        unique_session_id = chat_file.stem

                        sessions.append(
                            {
                                "cli": "gemini",
                                "session_id": unique_session_id,
                                "file_path": str(chat_file),
                                "project_hash": project_hash,
                                "created_at": chat_file.stat().st_ctime,
                                "start_time": chat_data.get("startTime"),
                                "last_updated": chat_data.get("lastUpdated"),
                                "message_count": len(chat_data.get("messages", [])),
                                "file_size": file_size,
                                "first_message": session_metadata.get(gemini_session_id, {}).get(
                                    "first_message", ""
                                ),
                            }
                        )
                    except (OSError, json.JSONDecodeError, MemoryError) as e:
                        logger.error(f"Error parsing Gemini chat file {chat_file}: {e}")
                        continue

        return sessions

    @staticmethod
    def ingest(session: dict, dest_dir: Path) -> bool:
        """Ingest one Gemini session: convert JSON to JSONL with normalized filename.

        Extracts canonical session_id from file to normalize filename to {uuid}.jsonl.
        """
        return base.ingest_session_transform(
            session, dest_dir, "gemini", Gemini.session_id_from_contents, Gemini.to_jsonl
        )

    @staticmethod
    def index(session_id: str) -> int:
        """Index one Gemini session into database."""
        return base.index_session(session_id, "gemini")

    @staticmethod
    def parse(file_path: Path | str, from_offset: int = 0) -> list[SessionMessage]:
        """Parse Gemini session data to unified event format.

        Accepts file path or raw JSONL string content.
        """

        def parse_line(obj: dict, line_num: int) -> list[SessionMessage]:
            events = []
            msg_type = obj.get("type")
            timestamp = obj.get("timestamp")

            if msg_type == "model":
                events.extend(Gemini._parse_model_message(obj.get("parts", []), timestamp))
            elif msg_type == "user":
                events.extend(Gemini._parse_user_message(obj.get("parts", []), timestamp))

            return events

        return base.parse_jsonl_file(file_path, parse_line, from_offset)

    @staticmethod
    def tokens(file_path: Path) -> tuple[int | None, int | None]:
        """Extract input and output tokens from Gemini files.

        Note: Synced JSONL files don't contain token data (stripped during conversion).
        Only raw JSON source files have token info.
        """
        input_total = 0
        output_total = 0
        found_any = False
        try:
            with open(file_path) as f:
                first_char = f.read(1)
                if not first_char:
                    return (None, None)
                f.seek(0)

                # Check if JSON (starts with {) or JSONL
                if first_char == "{":
                    # Try as single JSON object (raw Gemini format)
                    try:
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
                    except json.JSONDecodeError:
                        # Not valid JSON, tokens unavailable
                        pass
                # JSONL format - token data not preserved in conversion
        except OSError as e:
            logger.error(f"Error extracting Gemini tokens from {file_path}: {e}")
        return (input_total if found_any else None, output_total if found_any else None)

    @staticmethod
    def session_id_from_stream(output: str) -> str | None:
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
    def session_id_from_contents(file_path: Path) -> str | None:
        """Extract session_id from Gemini session file contents.

        Gemini stores sessionId in JSON root under 'sessionId' field.
        """
        try:
            with open(file_path) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get("sessionId")
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to extract session_id from {file_path}: {e}")
        return None

    @staticmethod
    def _parse_model_message(parts: list, timestamp: str | None) -> list[SessionMessage]:
        """Extract function calls and text from model message."""
        messages = []

        for part in parts:
            if isinstance(part, dict):
                if "text" in part:
                    messages.append(
                        SessionMessage(
                            type="text", timestamp=timestamp, content=part.get("text", "")
                        )
                    )

                elif "functionCall" in part:
                    fn_call = part.get("functionCall", {})
                    messages.append(
                        SessionMessage(
                            type="tool_call",
                            timestamp=timestamp,
                            content={
                                "tool_name": fn_call.get("name", ""),
                                "input": fn_call.get("args", {}),
                            },
                        )
                    )

        return messages

    @staticmethod
    def _parse_user_message(parts: list, timestamp: str | None) -> list[SessionMessage]:
        """Extract function results from user message."""
        messages = []

        for part in parts:
            if isinstance(part, dict) and "functionResult" in part:
                fn_result = part.get("functionResult", {})
                result_data = fn_result.get("response", {})
                messages.append(
                    SessionMessage(
                        type="tool_result",
                        timestamp=timestamp,
                        content={
                            "output": result_data.get("result", "")
                            if isinstance(result_data, dict)
                            else str(result_data),
                            "is_error": False,
                        },
                    )
                )

        return messages

    @staticmethod
    def to_jsonl(json_file: Path) -> str:
        """Convert Gemini JSON session to JSONL format.

        Gemini stores sessions as JSON, but space-os uses JSONL uniformly.
        Filters out system messages (internal continuation prompts).

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
                    msg_type = msg.get("type")
                    if msg_type not in ("user", "model"):
                        continue

                    content = msg.get("content", "")
                    if not content:
                        continue

                    if isinstance(content, list):
                        content = "\n".join(
                            [
                                block.get("text", "")
                                if isinstance(block, dict) and block.get("type") == "text"
                                else ""
                                for block in content
                            ]
                        ).strip()

                    if not content:
                        continue

                    if is_system_bloat(content):
                        continue

                    lines.append(
                        json.dumps(
                            {
                                "role": "assistant" if msg_type == "model" else "user",
                                "content": str(content),
                                "timestamp": msg.get("timestamp"),
                            }
                        )
                    )
            return "\n".join(lines) + "\n" if lines else ""
        except (OSError, json.JSONDecodeError):
            return ""
