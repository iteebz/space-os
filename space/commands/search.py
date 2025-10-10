import json

import typer

from ..bridge import config as bridge_config
from ..knowledge import db as knowledge_db
from ..lib import db as libdb
from ..memory import db as memory_db


def search(
    keyword: str = typer.Argument(..., help="Keyword to search"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Search across memory, knowledge, and bridge."""
    results = {"memory": [], "knowledge": [], "bridge": []}

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
            rows = conn.execute(
                "SELECT agent_id, topic, message FROM memory WHERE message LIKE ? AND archived_at IS NULL",
                (f"%{keyword}%",),
            ).fetchall()
            results["memory"] = [{"identity": r[0], "topic": r[1], "message": r[2]} for r in rows]

    if knowledge_db.database_path().exists():
        with knowledge_db.connect() as conn:
            rows = conn.execute(
                "SELECT domain, content, agent_id FROM knowledge WHERE (content LIKE ? OR domain LIKE ?) AND archived_at IS NULL",
                (f"%{keyword}%", f"%{keyword}%"),
            ).fetchall()
            results["knowledge"] = [
                {"domain": r[0], "content": r[1], "contributor": r[2]} for r in rows
            ]

    if bridge_config.DB_PATH.exists():
        with libdb.connect(bridge_config.DB_PATH) as conn:
            rows = conn.execute(
                "SELECT c.name, m.agent_id, m.content FROM messages m JOIN channels c ON m.channel_id = c.id WHERE m.content LIKE ? AND c.archived_at IS NULL",
                (f"%{keyword}%",),
            ).fetchall()
            results["bridge"] = [{"channel": r[0], "sender": r[1], "content": r[2]} for r in rows]

    if json_output:
        typer.echo(json.dumps(results))
        return

    if quiet_output:
        return

    total = len(results["memory"]) + len(results["knowledge"]) + len(results["bridge"])
    if total == 0:
        typer.echo(f"No results for '{keyword}'")
        return

    typer.echo(
        f"Found in memory ({len(results['memory'])}), knowledge ({len(results['knowledge'])}), bridge ({len(results['bridge'])})\n"
    )

    if results["memory"]:
        typer.echo("MEMORY:")
        for r in results["memory"][:5]:
            typer.echo(f"  [{r['identity']}] {r['topic']}: {r['message'][:80]}")
        typer.echo()

    if results["knowledge"]:
        typer.echo("KNOWLEDGE:")
        for r in results["knowledge"][:5]:
            typer.echo(f"  [{r['domain']}] {r['content'][:80]}")
        typer.echo()

    if results["bridge"]:
        typer.echo("BRIDGE:")
        for r in results["bridge"][:5]:
            typer.echo(f"  [{r['channel']}] {r['sender']}: {r['content'][:80]}")
