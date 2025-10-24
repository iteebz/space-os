"""Chats: sync and search chat logs across Claude/Codex/Gemini."""

import typer

from space.os.lib.chats import (
    get_entry,
    get_surrounding_context,
    list_entries,
    sample,
    search,
    sync,
)

app = typer.Typer(help="Search and manage chat logs")


@app.command()
def sync_cmd(
    identity: str | None = typer.Option(
        None, "--identity", "-i", help="Tag synced entries with identity"
    ),
):
    """Sync all CLIs with optional identity tag."""
    results = sync(identity=identity)

    total = sum(results.values())
    typer.echo(f"Synced {total:,} entries")
    typer.echo(f"  claude: {results['claude']:,}")
    typer.echo(f"  codex:  {results['codex']:,}")
    typer.echo(f"  gemini: {results['gemini']:,}")

    if identity:
        typer.echo(f"\nTagged as: {identity}")


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
