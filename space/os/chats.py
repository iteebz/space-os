import hashlib
import sqlite3
from typing import Any

import typer

from space.os import db
from space.os.lib import agents
from space.os.lib.models import Message


def schema() -> str:
    """Chat database schema."""
    return """
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
);

CREATE INDEX IF NOT EXISTS idx_identity ON entries(identity);
CREATE INDEX IF NOT EXISTS idx_cli_session ON entries(cli, session_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON entries(timestamp);
"""


db.register("chats", "chats.db", schema())
db.add_migrations("chats", [])


def _insert_msgs(cli: str, msgs: list[Message], identity: str) -> int:
    synced = 0
    with db.ensure("chats") as conn:
        conn.row_factory = sqlite3.Row
        for msg in msgs:
            raw_hash = hashlib.sha256(
                f"{cli}{msg.session_id}{msg.timestamp}{msg.text}".encode()
            ).hexdigest()
            try:
                conn.execute(
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
                        identity,
                        msg.role,
                        msg.text,
                        raw_hash,
                    ),
                )
                synced += 1
            except sqlite3.IntegrityError:
                pass
    return synced


def sync(identity: str) -> dict[str, int]:
    """Sync CLI sessions for a specific identity. Called on wake."""
    init_db()
    return {
        "claude": _insert_msgs("claude", agents.claude.sessions(), identity),
        "codex": _insert_msgs("codex", agents.codex.sessions(), identity),
        "gemini": _insert_msgs("gemini", agents.gemini.sessions(), identity),
    }


def search(query: str, identity: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    with db.ensure("chats") as conn:
        conn.row_factory = sqlite3.Row

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

        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def list_entries(identity: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    with db.ensure("chats") as conn:
        conn.row_factory = sqlite3.Row

        sql = """
            SELECT id, cli, model, session_id, timestamp, identity, role, text
            FROM entries
            WHERE 1=1
        """
        params = []

        if identity:
            sql += " AND identity = ?"
            params.append(identity)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def get_entry(entry_id: int) -> dict[str, Any] | None:
    with db.ensure("chats") as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        return dict(row) if row else None


def get_surrounding_context(entry_id: int, context_size: int = 5) -> list[dict[str, Any]]:
    entry = get_entry(entry_id)
    if not entry:
        return []

    with db.ensure("chats") as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, cli, model, session_id, timestamp, identity, role, text
            FROM entries
            WHERE cli = ? AND session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (entry["cli"], entry["session_id"], context_size * 2),
        ).fetchall()
        return [dict(row) for row in rows]


def sample(
    count: int = 5, identity: str | None = None, cli: str | None = None
) -> list[dict[str, Any]]:
    with db.ensure("chats") as conn:
        conn.row_factory = sqlite3.Row

        sql = "SELECT id, cli, model, session_id, timestamp, identity, role, text FROM entries WHERE 1=1"
        params = []

        if identity:
            sql += " AND identity = ?"
            params.append(identity)

        if cli:
            sql += " AND cli = ?"
            params.append(cli)

        sql += " ORDER BY RANDOM() LIMIT ?"
        params.append(count)

        return [dict(row) for row in conn.execute(sql, params).fetchall()]


app = typer.Typer(help="Search and manage chat logs")


@app.command()
def sync_cmd(
    identity: str = typer.Option(..., "--as", help="Identity to sync chats for"),
):
    """Sync CLI sessions for an identity."""
    results = sync(identity=identity)

    total = sum(results.values())
    typer.echo(f"Synced {total:,} entries for {identity}")
    if results["claude"]:
        typer.echo(f"  claude: {results['claude']:,}")
    if results["codex"]:
        typer.echo(f"  codex:  {results['codex']:,}")
    if results["gemini"]:
        typer.echo(f"  gemini: {results['gemini']:,}")


@app.command()
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    identity: str | None = typer.Option(None, "--identity", "-i", help="Filter by identity"),
    limit: int = typer.Option(10, "--limit", "-l", help="Result limit"),
):
    """Search logged decisions."""
    results = search(query, identity=identity, limit=limit)

    if not results:
        typer.echo(f"No results for '{query}'")
        return

    typer.echo(f"Found {len(results)} result(s):\n")
    for entry in results:
        typer.echo(f"[{entry['id']}] {entry['cli']} @ {entry['timestamp'][:16]}")
        typer.echo(f"    text: {entry['text'][:80]}...")
        typer.echo()


@app.command()
def list_cmd(
    identity: str | None = typer.Option(None, "--identity", "-i", help="Filter by identity"),
    limit: int = typer.Option(20, "--limit", "-l", help="Result limit"),
):
    """List recent entries."""
    entries = list_entries(identity=identity, limit=limit)

    if not entries:
        typer.echo("No entries")
        return

    typer.echo(f"Recent {len(entries)} entries:\n")
    for e in entries:
        tag = f" ({e['identity']})" if e["identity"] else ""
        typer.echo(f"[{e['id']}] {e['cli']}{tag} - {e['timestamp'][:16]}")
        typer.echo(f"     {e['text'][:70]}...")
        typer.echo()


@app.command()
def view(
    entry_id: int = typer.Argument(..., help="Entry ID"),
    context: int = typer.Option(5, "--context", "-c", help="Context window size"),
):
    """View a specific entry with context."""
    entry = get_entry(entry_id)

    if not entry:
        typer.echo(f"Entry {entry_id} not found")
        return

    typer.echo(f"Entry {entry_id}:")
    typer.echo(f"  CLI: {entry['cli']}")
    typer.echo(f"  Session: {entry['session_id']}")
    typer.echo(f"  Role: {entry['role']}")
    typer.echo(f"  Timestamp: {entry['timestamp']}")
    typer.echo(f"  Identity: {entry['identity'] or 'untagged'}")
    typer.echo()

    typer.echo("Text:")
    typer.echo(f"  {entry['text']}")

    if context:
        ctx_entries = get_surrounding_context(entry_id, context_size=context)
        if ctx_entries:
            typer.echo(f"\nSurrounding context ({len(ctx_entries)} entries):")
            for c in ctx_entries[:5]:
                if c["id"] == entry_id:
                    typer.echo(f"  → [{c['id']}] {c['timestamp'][:16]} (THIS)")
                else:
                    typer.echo(f"    [{c['id']}] {c['timestamp'][:16]}")


@app.command()
def sample_cmd(
    count: int = typer.Option(5, "--count", "-c", help="Number of samples"),
    identity: str | None = typer.Option(None, "--identity", "-i", help="Filter by identity"),
    cli: str | None = typer.Option(None, "--cli", help="Filter by CLI (claude, codex, gemini)"),
):
    """Sample random entries from database."""
    entries = sample(count, identity=identity, cli=cli)

    if not entries:
        typer.echo("No entries found")
        return

    typer.echo(f"Random sample ({len(entries)} entries):\n")
    for e in entries:
        model = e["model"] or "unknown"
        typer.echo(f"[{e['id']}] {e['cli']:8} {model:25} {e['role']}")
        typer.echo(f"     {e['text'][:90]}")
        if len(e["text"]) > 90:
            typer.echo("     ...")
        typer.echo()
