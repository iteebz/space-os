import json
from abc import ABC, abstractmethod
from pathlib import Path


class ChatProvider(ABC):
    @abstractmethod
    def discover_sessions(self) -> list[dict]:
        """Return list of {session_id, file_path, created_at}."""
        pass

    @abstractmethod
    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from offset, return [{role, content, timestamp, ...}]."""
        pass


class ClaudeProvider(ChatProvider):
    def __init__(self):
        self.chats_dir = Path.home() / ".claude" / "projects"

    def discover_sessions(self) -> list[dict]:
        sessions = []
        if not self.chats_dir.exists():
            return sessions

        for jsonl in self.chats_dir.glob("*.jsonl"):
            sessions.append({
                "cli": "claude",
                "session_id": jsonl.stem,
                "file_path": str(jsonl),
                "created_at": jsonl.stat().st_ctime,
            })
        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
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
                    if role not in ("user", "assistant"):
                        continue
                    messages.append({
                        "role": role,
                        "content": data.get("message", ""),
                        "timestamp": data.get("timestamp"),
                        "byte_offset": offset,
                    })
        except (OSError, json.JSONDecodeError):
            pass
        return messages


class CodexProvider(ChatProvider):
    def __init__(self):
        self.sessions_dir = Path.home() / ".codex" / "sessions"

    def discover_sessions(self) -> list[dict]:
        sessions = []
        if not self.sessions_dir.exists():
            return sessions

        for jsonl in self.sessions_dir.rglob("*.jsonl"):
            sessions.append({
                "cli": "codex",
                "session_id": jsonl.stem,
                "file_path": str(jsonl),
                "created_at": jsonl.stat().st_ctime,
            })
        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        messages = []
        try:
            with open(file_path, "rb") as f:
                f.seek(from_offset)
                for line in f:
                    if not line.strip():
                        continue
                    offset = f.tell() - len(line)
                    data = json.loads(line)
                    if data.get("type") != "response_item":
                        continue
                    payload = data.get("payload", {})
                    role = payload.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    messages.append({
                        "role": role,
                        "content": payload.get("content", ""),
                        "timestamp": data.get("timestamp"),
                        "byte_offset": offset,
                    })
        except (OSError, json.JSONDecodeError):
            pass
        return messages


class GeminiProvider(ChatProvider):
    def __init__(self):
        self.tmp_dir = Path.home() / ".gemini" / "tmp"

    def discover_sessions(self) -> list[dict]:
        sessions = []
        if not self.tmp_dir.exists():
            return sessions

        for subdir in self.tmp_dir.iterdir():
            if not subdir.is_dir():
                continue
            for json_file in subdir.glob("session-*.json"):
                sessions.append({
                    "cli": "gemini",
                    "session_id": json_file.stem,
                    "file_path": str(json_file),
                    "created_at": json_file.stat().st_ctime,
                })
        return sessions

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        messages = []
        try:
            with open(file_path) as f:
                data = json.load(f)
            
            for i, msg in enumerate(data.get("messages", [])):
                if i < from_offset:
                    continue
                role = msg.get("role") or msg.get("type")
                if role not in ("user", "model", "assistant"):
                    continue
                if role == "model":
                    role = "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp"),
                    "message_index": i,
                })
        except (OSError, json.JSONDecodeError):
            pass
        return messages


PROVIDERS = {
    "claude": ClaudeProvider(),
    "codex": CodexProvider(),
    "gemini": GeminiProvider(),
}


def get_provider(cli: str) -> ChatProvider:
    """Get provider instance by CLI name."""
    return PROVIDERS.get(cli)
