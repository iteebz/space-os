import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".space" / "sessions.db"


@dataclass
class SessionMsg:
    """Canonical message format across all CLIs."""

    role: str  # "user" or "assistant"
    text: str  # Plain text content
    timestamp: str  # ISO8601
    session_id: str
    model: str | None = None  # Model name (claude-sonnet-4.5, gpt-5-codex, etc)

    def is_valid(self) -> bool:
        """Check if message has required fields."""
        return bool(self.role and self.text and self.timestamp and self.session_id)


def init_db():
    """Create sessions.db schema if not exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cli TEXT NOT NULL,
            model TEXT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            identity TEXT,
            role TEXT NOT NULL,
            text TEXT NOT NULL,
            raw_hash TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(cli, session_id, timestamp)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_identity ON entries(identity)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cli_session ON entries(cli, session_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON entries(timestamp)
    """)

    conn.commit()
    conn.close()


def _extract_text(content: Any) -> str:
    """Extract plain text from various content formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        text_field = content.get("text") or content.get("content") or ""
        if isinstance(text_field, list):
            return " ".join(
                str(t.get("text", "") if isinstance(t, dict) else t) for t in text_field
            ).strip()
        return str(text_field)
    if isinstance(content, list):
        return " ".join(
            str(item.get("text", "") if isinstance(item, dict) else item) for item in content
        ).strip()
    return str(content) if content else ""


def _norm_msgs(path: Path, extractor) -> list[SessionMsg]:
    """Generic message normalizer."""
    try:
        raw_msgs = extractor(path)
        return [m for m in raw_msgs if m.is_valid()]
    except (OSError, json.JSONDecodeError):
        return []


def norm_claude_jsonl(path: Path) -> list[SessionMsg]:
    """Normalize Claude JSONL to canonical format."""

    def extract(p: Path) -> list[SessionMsg]:
        msgs = []
        with open(p) as f:
            for line in f:
                if not line.strip():
                    continue
                raw = json.loads(line)
                role = raw.get("type")
                if role not in ("user", "assistant"):
                    continue
                text = _extract_text(raw.get("message"))
                if not text:
                    continue
                msgs.append(
                    SessionMsg(
                        role=role,
                        text=text,
                        timestamp=raw.get("timestamp", datetime.now().isoformat()),
                        session_id=str(p.stem),
                    )
                )
        return msgs

    return _norm_msgs(path, extract)


def norm_codex_jsonl(path: Path) -> list[SessionMsg]:
    """Normalize Codex JSONL to canonical format."""

    def extract(p: Path) -> list[SessionMsg]:
        msgs = []
        with open(p) as f:
            for line in f:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if raw.get("type") != "response_item":
                    continue
                payload = raw.get("payload", {})
                role = payload.get("role")
                if role not in ("user", "assistant"):
                    continue
                text = _extract_text(payload.get("content"))
                if not text:
                    continue
                msgs.append(
                    SessionMsg(
                        role=role,
                        text=text,
                        timestamp=raw.get("timestamp", datetime.now().isoformat()),
                        session_id=str(p.stem),
                    )
                )
        return msgs

    return _norm_msgs(path, extract)


def norm_gemini_json(path: Path) -> list[SessionMsg]:
    """Normalize Gemini JSON to canonical format."""

    def extract(p: Path) -> list[SessionMsg]:
        msgs = []
        with open(p) as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return msgs
            session_id = data.get("sessionId", str(p.stem))
            for raw in data.get("messages", []):
                role = raw.get("role") or raw.get("type")
                if role not in ("user", "model", "assistant"):
                    continue
                if role == "model":
                    role = "assistant"
                text = _extract_text(raw.get("content"))
                if not text:
                    continue
                msgs.append(
                    SessionMsg(
                        role=role,
                        text=text,
                        timestamp=raw.get("timestamp", datetime.now().isoformat()),
                        session_id=session_id,
                    )
                )
        return msgs

    return _norm_msgs(path, extract)


def extract_decision(user_prompt: str, assistant_response: str) -> tuple[str | None, str | None]:
    """Extract decision and outcome from a prompt-response pair."""
    if not assistant_response:
        return None, "no_response"

    # For now, just extract first ~500 chars of assistant response as decision
    # In production, this would use LLM to extract actual decisions
    response_text = ""
    if isinstance(assistant_response, dict):
        content = assistant_response.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    response_text += block.get("text", "")
                elif isinstance(block, str):
                    response_text += block
        else:
            response_text = str(content)
    else:
        response_text = str(assistant_response)

    decision = response_text[:500] if response_text else None
    outcome = "success" if decision else "no_response"

    return decision, outcome


def _insert_msgs(cli: str, msgs: list[SessionMsg]) -> int:
    """Insert messages batch into DB."""
    synced = 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for msg in msgs:
        raw_hash = hashlib.sha256(
            f"{cli}{msg.session_id}{msg.timestamp}{msg.text}".encode()
        ).hexdigest()
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO entries
                (cli, model, session_id, timestamp, identity, role, text, raw_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    cli,
                    msg.model,
                    msg.session_id,
                    msg.timestamp,
                    None,
                    msg.role,
                    msg.text,
                    raw_hash,
                ),
            )
            synced += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return synced


def sync_claude():
    """Sync Claude Code sessions."""
    init_db()
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return 0
    msgs = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            msgs.extend(norm_claude_jsonl(jsonl_file))
    return _insert_msgs("claude", msgs)


def sync_codex():
    """Sync Codex CLI sessions."""
    init_db()
    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.exists():
        return 0
    msgs = []
    model_cache = {}
    for jsonl_file in sessions_dir.rglob("*.jsonl"):
        if jsonl_file not in model_cache:
            model = None
            with open(jsonl_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    if raw.get("type") == "turn_context":
                        model = raw.get("payload", {}).get("model")
                        break
            model_cache[jsonl_file] = model
        for msg in norm_codex_jsonl(jsonl_file):
            msg.model = model_cache[jsonl_file]
            msgs.append(msg)
    return _insert_msgs("codex", msgs)


def sync_gemini():
    """Sync Gemini CLI sessions."""
    init_db()
    gemini_dir = Path.home() / ".gemini" / "tmp"
    if not gemini_dir.exists():
        return 0
    msgs = []
    for json_file in gemini_dir.rglob("*.json"):
        if json_file.name == "logs.json":
            continue
        msgs.extend(norm_gemini_json(json_file))
    return _insert_msgs("gemini", msgs)


def sync(identity: str | None = None) -> dict[str, int]:
    """Sync all CLIs. Optionally tag with identity."""
    init_db()

    results = {
        "claude": sync_claude(),
        "codex": sync_codex(),
        "gemini": sync_gemini(),
    }

    if identity:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE entries SET identity = ? WHERE identity IS NULL", (identity,))
        conn.commit()
        conn.close()

    return results


def search(query: str, identity: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Search entries by query and optional identity."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = """
        SELECT id, cli, model, session_id, timestamp, identity, role, text
        FROM entries
        WHERE text LIKE ?
    """
    params = [f"%{query}%"]

    if identity:
        sql += " AND identity = ?"
        params.append(identity)

    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def list_entries(identity: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """List entries, optionally filtered by identity."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if identity:
        cursor.execute(
            """
            SELECT id, cli, model, session_id, timestamp, identity, role, text
            FROM entries
            WHERE identity = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (identity, limit),
        )
    else:
        cursor.execute(
            """
            SELECT id, cli, model, session_id, timestamp, identity, role, text
            FROM entries
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_entry(entry_id: int) -> dict[str, Any] | None:
    """Get a single entry with full context."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_surrounding_context(entry_id: int, context_size: int = 5) -> list[dict[str, Any]]:
    """Get entries surrounding a given entry (for memory context view)."""
    entry = get_entry(entry_id)
    if not entry:
        return []

    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get entries from same session near the timestamp
    cursor.execute(
        """
        SELECT id, cli, model, session_id, timestamp, identity, role, text
        FROM entries
        WHERE cli = ? AND session_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """,
        (entry["cli"], entry["session_id"], context_size * 2),
    )

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results


def sample(
    count: int = 5, identity: str | None = None, cli: str | None = None
) -> list[dict[str, Any]]:
    """Randomly sample entries from database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    sql = (
        "SELECT id, cli, model, session_id, timestamp, identity, role, text FROM entries WHERE 1=1"
    )
    params = []

    if identity:
        sql += " AND identity = ?"
        params.append(identity)

    if cli:
        sql += " AND cli = ?"
        params.append(cli)

    sql += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return results
