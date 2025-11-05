"""Claude provider: chat discovery and message parsing."""

import io
import json
import logging
import shutil
from pathlib import Path

from space.core.models import SessionMessage
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
    def launch_args(is_ephemeral: bool = False) -> list[str]:
        """Return launch arguments for Claude.

        Args:
            is_ephemeral: Whether this is an ephemeral spawn. Only ephemeral spawns skip permissions.
        """
        disallowed = [
            "NotebookRead",
            "NotebookEdit",
            "Task",
            "TodoWrite",
        ]
        args = ["--disallowedTools", ",".join(disallowed)]
        if is_ephemeral:
            args.insert(0, "--dangerously-skip-permissions")
        return args

    @staticmethod
    def task_launch_args() -> list[str]:
        """Return launch arguments for task-based Claude execution.

        Task mode uses stdin input and stream-json output format for real-time event streaming.
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
            "stream-json",
            "--disallowedTools",
            ",".join(disallowed),
        ]

    @staticmethod
    def discover() -> list[dict]:
        """Discover Claude sessions."""
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
        try:
            src_file = Path(session.get("file_path", ""))

            if not src_file.exists():
                return False

            session_id = Claude.session_id_from_contents(src_file)
            if not session_id:
                session_id = src_file.stem

            dest_file = dest_dir / f"{session_id}.jsonl"
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)
            return True
        except Exception as e:
            logger.error(f"Error ingesting Claude session: {e}")
        return False

    @staticmethod
    def index(session_id: str) -> int:
        """Index one Claude session into database."""
        from space.os.sessions.api.sync import _index_transcripts

        sessions_dir = Path.home() / ".space" / "sessions" / "claude"
        jsonl_file = sessions_dir / f"{session_id}.jsonl"

        if not jsonl_file.exists():
            return 0

        try:
            content = jsonl_file.read_text()
            return _index_transcripts(session_id, "claude", content)
        except Exception as e:
            logger.error(f"Error indexing Claude session {session_id}: {e}")
        return 0

    @staticmethod
    def parse(file_path: Path | str, from_offset: int = 0) -> list[SessionMessage]:
        """Parse Claude session data to unified message format.

        Accepts file path or raw JSONL string content.
        Emits all event types: messages, tool calls, and tool results.
        Consumers filter based on their needs (transcripts filters by type="message", trace includes all).
        """
        messages = []

        if isinstance(file_path, str):
            file_obj = io.StringIO(file_path)
        else:
            file_path = Path(file_path)
            if not file_path.exists():
                return messages
            file_obj = open(file_path)

        with file_obj:
            for line in file_obj:
                if not line.strip():
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

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

    @staticmethod
    def tokens(file_path: Path) -> tuple[int | None, int | None]:
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
    def session_id_from_stream(output: str) -> str | None:
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
    def session_id_from_contents(file_path: Path) -> str | None:
        """Extract session_id from Claude JSONL file contents.

        Claude stores sessionId in first line of JSONL.
        """
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
        """Extract tool calls and text from assistant message."""
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
        """Extract tool results from user message."""
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
