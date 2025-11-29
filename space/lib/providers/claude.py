"""Claude provider: chat discovery and message parsing."""

import json
import logging
from pathlib import Path

from space.core.models import SessionMessage
from space.core.protocols import Provider

from . import base

logger = logging.getLogger(__name__)


class Claude(Provider):
    SESSIONS_DIR = Path.home() / ".claude" / "projects"
    DISALLOWED_TOOLS = ["NotebookRead", "NotebookEdit", "Task", "TodoWrite"]

    @staticmethod
    def escape_cwd(cwd: str) -> str:
        """Escape CWD for Claude's project directory naming."""
        return cwd.replace("/", "-").replace(".", "-")

    @staticmethod
    def extract_session_id(output: str) -> str | None:
        """Extract session ID from Claude CLI JSONL output.

        Format: Line 2 contains "sessionId":"<uuid>"
        """
        lines = output.strip().split("\n")
        if len(lines) < 2:
            return None

        try:
            data = json.loads(lines[1])
            return data.get("sessionId")
        except (json.JSONDecodeError, KeyError, IndexError):
            return None

    @staticmethod
    def allowed_tools() -> list[str]:
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
    def launch_args() -> list[str]:
        return ["--disallowedTools", ",".join(Claude.DISALLOWED_TOOLS)]

    @staticmethod
    def task_launch_args() -> list[str]:
        return [
            "--print",
            "--dangerously-skip-permissions",
            "--disallowedTools",
            ",".join(Claude.DISALLOWED_TOOLS),
        ]

    @staticmethod
    def discover_session(
        spawn, start_ts: float, end_ts: float, cwd: str | None = None
    ) -> str | None:
        """Discover Claude session created during spawn window.

        Args:
            spawn: Spawn object (unused, kept for interface compatibility)
            start_ts: Window start timestamp
            end_ts: Window end timestamp
            cwd: If provided, only search in project dir for this CWD

        Strategy: Match sessions by mtime within spawn time window.
        Returns closest match to spawn start time.
        """
        candidates = []

        if cwd:
            project_dir = Claude.SESSIONS_DIR / Claude.escape_cwd(cwd)
            search_dirs = [project_dir] if project_dir.is_dir() else []
        else:
            search_dirs = [d for d in Claude.SESSIONS_DIR.iterdir() if d.is_dir()]

        for project_dir in search_dirs:
            for session_file in project_dir.glob("*.jsonl"):
                try:
                    mtime = session_file.stat().st_mtime
                    if start_ts <= mtime <= end_ts:
                        candidates.append((session_file.stem, abs(mtime - start_ts)))
                except OSError:
                    continue

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]

    @staticmethod
    def session_exists(session_id: str, expected_cwd: str | None = None) -> bool:
        """Check if Claude CLI can resume this session.

        Args:
            session_id: Session ID to validate
            expected_cwd: If provided, also validate session CWD matches
        """
        if not Claude.SESSIONS_DIR.exists():
            return False

        for jsonl in Claude.SESSIONS_DIR.rglob("*.jsonl"):
            if jsonl.stem == session_id:
                if not expected_cwd:
                    return True

                # Validate CWD matches (check first few lines for user message with cwd)
                try:
                    with open(jsonl) as f:
                        for _ in range(5):  # Check first 5 lines
                            line = f.readline()
                            if not line.strip():
                                continue
                            obj = json.loads(line)
                            if obj.get("cwd"):
                                return obj["cwd"] == expected_cwd
                except (OSError, json.JSONDecodeError, ValueError):
                    pass
                return False
        return False

    @staticmethod
    def discover() -> list[dict]:
        sessions = []
        if not Claude.SESSIONS_DIR.exists():
            return sessions

        for jsonl in Claude.SESSIONS_DIR.rglob("*.jsonl"):
            session_id = Claude.session_id_from_contents(jsonl)
            if not session_id:
                session_id = jsonl.stem
                logger.debug(f"Falling back to filename for Claude session: {jsonl}")
            sessions.append(
                {
                    "cli": "claude",
                    "session_id": session_id,
                    "file_path": str(jsonl),
                    "created_at": jsonl.stat().st_ctime,
                }
            )
        return sessions

    @staticmethod
    def ingest(session: dict, dest_dir: Path) -> bool:
        """Ingest one Claude session: copy to destination with normalized filename.

        Extracts canonical session_id from file, falls back to filename if extraction fails.
        """

        def extract_id(src_file: Path) -> str | None:
            session_id = Claude.session_id_from_contents(src_file)
            return session_id or src_file.stem

        return base.ingest_session_copy(session, dest_dir, "claude", extract_id)

    @staticmethod
    def index(session_id: str) -> int:
        return base.index_session(session_id, "claude")

    @staticmethod
    def parse(file_path: Path | str, from_offset: int = 0) -> list[SessionMessage]:
        def parse_line(obj: dict, line_num: int) -> list[SessionMessage]:
            messages = []
            msg_type = obj.get("type")
            timestamp = obj.get("timestamp")
            message = obj.get("message", {})

            if msg_type == "assistant":
                messages.extend(Claude._parse_assistant_message(message, timestamp))

                if isinstance(message, dict) and message.get("role"):
                    messages.append(
                        SessionMessage(
                            type="message",
                            timestamp=timestamp,
                            content={
                                "role": message.get("role"),
                                "text": message.get("content", ""),
                            },
                        )
                    )
            elif msg_type == "user":
                messages.extend(Claude._parse_user_message(message, timestamp))

                if isinstance(message, dict) and message.get("role"):
                    messages.append(
                        SessionMessage(
                            type="message",
                            timestamp=timestamp,
                            content={
                                "role": message.get("role"),
                                "text": message.get("content", ""),
                            },
                        )
                    )

            return messages

        return base.parse_jsonl_file(file_path, parse_line, from_offset)

    @staticmethod
    def tokens(file_path: Path) -> tuple[int | None, int | None]:
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
                                # Only count completed turns (not streaming chunks)
                                stop_reason = msg.get("stop_reason")
                                if stop_reason not in ("end_turn", "tool_use"):
                                    continue
                                usage = msg["usage"]
                                inp = usage.get("input_tokens", 0)
                                inp += usage.get("cache_read_input_tokens", 0)
                                inp += usage.get("cache_creation_input_tokens", 0)
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
    def session_id_from_stream(output: str) -> str | None:
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                return data.get("session_id")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Claude headless output: {e}")
        return None

    @staticmethod
    def session_id_from_contents(file_path: Path) -> str | None:
        try:
            with open(file_path) as f:
                first_line = f.readline()
                if not first_line.strip():
                    return None
                obj = json.loads(first_line)
                if isinstance(obj, dict):
                    return obj.get("sessionId")
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to extract session_id from {file_path}: {e}")
        return None

    @staticmethod
    def _parse_assistant_message(message: dict, timestamp: str | None) -> list[SessionMessage]:
        messages = []
        content = message.get("content", [])

        if not isinstance(content, list):
            return messages

        for item in content:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")

            if item_type == "tool_use":
                messages.append(
                    SessionMessage(
                        type="tool_call",
                        timestamp=timestamp,
                        content={
                            "tool_name": item.get("name", ""),
                            "input": item.get("input", {}),
                        },
                    )
                )

            elif item_type == "text":
                messages.append(
                    SessionMessage(
                        type="text",
                        timestamp=timestamp,
                        content=item.get("text", ""),
                    )
                )

        return messages

    @staticmethod
    def _parse_user_message(message: dict, timestamp: str | None) -> list[SessionMessage]:
        messages = []
        content = message.get("content", [])

        if not isinstance(content, list):
            return messages

        for item in content:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type")

            if item_type == "tool_result":
                messages.append(
                    SessionMessage(
                        type="tool_result",
                        timestamp=timestamp,
                        content={
                            "output": item.get("content", ""),
                            "is_error": item.get("is_error", False),
                        },
                    )
                )

        return messages
