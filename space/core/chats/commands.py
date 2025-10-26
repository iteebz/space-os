"""CLI commands for chats primitive."""

import typer

from space.lib import db as db_lib
from . import api, db

app = typer.Typer(help="Chat session management")


@app.command()
def sync():
    """Discover and sync all chat sessions from providers into chats.db."""
    db.register()
    typer.echo("Scanning providers for chat sessions...")
    
    discovery = api.discover()
    typer.echo(f"  ✓ Claude: {discovery.get('claude', 0)} sessions")
    typer.echo(f"  ✓ Codex: {discovery.get('codex', 0)} sessions")
    typer.echo(f"  ✓ Gemini: {discovery.get('gemini', 0)} sessions")
    
    total = sum(discovery.values())
    typer.echo(f"\n✓ Discovered {total} sessions")
    
    typer.echo("\nSyncing messages...")
    synced = 0
    for cli in ["claude", "codex", "gemini"]:
        count = api.sync(session_id=None, identity=None, cli=cli)
        synced += count
        if count > 0:
            typer.echo(f"  ✓ {cli.capitalize()}: {count} messages synced")
    
    typer.echo(f"\n✓ Total: {synced} messages synced")


@app.command()
def stats():
    """Show chat ingestion statistics."""
    db.register()
    
    typer.echo("Chat Statistics\n")
    
    with db_lib.ensure("chats") as conn:
        # Sessions per provider
        providers_data = conn.execute(
            "SELECT cli, COUNT(*) as count FROM sessions GROUP BY cli ORDER BY cli"
        ).fetchall()
        
        if not providers_data:
            typer.echo("No sessions found. Run 'chats sync' first.")
            return
        
        typer.echo("Sessions per provider:")
        total_sessions = 0
        for row in providers_data:
            cli = row["cli"].capitalize()
            count = row["count"]
            total_sessions += count
            typer.echo(f"  {cli}: {count}")
        
        typer.echo(f"\nTotal sessions: {total_sessions}")
        
        # Sessions with identity linked
        linked = conn.execute(
            "SELECT COUNT(*) as count FROM sessions WHERE identity IS NOT NULL"
        ).fetchone()
        typer.echo(f"Sessions linked to identity: {linked['count']}")
        
        # Sessions with task linked
        task_linked = conn.execute(
            "SELECT COUNT(*) as count FROM sessions WHERE task_id IS NOT NULL"
        ).fetchone()
        typer.echo(f"Sessions linked to task: {task_linked['count']}")


if __name__ == "__main__":
    app()
