"""Sessions CLI: agent execution history and self-reflection."""

from typing import Annotated

import typer

from space.lib import paths
from space.os.sessions import api

sessions_app = typer.Typer(invoke_without_command=True, add_completion=False, no_args_is_help=True)


@sessions_app.callback(invoke_without_command=True)
def sessions_callback(ctx: typer.Context):
    """Agent execution history and self-reflection.

    Query by agent identity to list spawns, or by spawn_id to view session logs.
    """
    pass


@sessions_app.command(name="query")
def query_cmd(
    query: Annotated[str, typer.Argument(help="Agent identity, spawn_id, or session_id")],
):
    """Query session details by spawn_id or list spawns by agent identity."""
    ctx = typer.get_current_context()
    ctx.invoke(show_session, query=query)


@sessions_app.command(name="sync")
def sync_cmd():
    """Sync sessions from provider CLIs (Claude, Gemini, Codex) to ~/.space/sessions/."""

    sessions_dir = paths.sessions_dir()

    def count_files(provider: str) -> int:
        """Count JSONL files for a provider."""
        provider_dir = sessions_dir / provider
        if not provider_dir.exists():
            return 0
        return len(list(provider_dir.glob("*.jsonl")))

    before = {p: count_files(p) for p in ["claude", "codex", "gemini"]}

    from space.lib.spinner import Spinner

    spinner = Spinner()
    last_count = -1

    def on_progress(event):
        nonlocal last_count
        count = event.total_synced
        if count != last_count:
            last_count = count
            spinner.update(f"Processing {count} files...")

    api.sync.sync_all(on_progress=on_progress)

    after = {p: count_files(p) for p in ["claude", "codex", "gemini"]}

    total_count = sum(after.values())

    spinner.finish(f"Processed {total_count} files")

    typer.echo("\nSession files in ~/.space/sessions:")
    typer.echo(f"{'Provider':<10} {'Before':<8} {'After':<8} {'Added'}")
    typer.echo("-" * 36)
    for provider in ["claude", "codex", "gemini"]:
        added = after[provider] - before[provider]
        typer.echo(f"{provider:<10} {before[provider]:<8} {after[provider]:<8} {added}")
    typer.echo("-" * 36)


def show_session(query: str):
    """Show session details by spawn_id or list spawns by identity."""
    from space.core.models import Spawn
    from space.lib import store
    from space.lib.store import from_row

    # Try as spawn_id first (partial match supported)
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT * FROM spawns WHERE id = ? OR id LIKE ? LIMIT 1",
            (query, f"{query}%"),
        ).fetchone()
        if row:
            spawn = from_row(row, Spawn)
            _show_spawn_session(spawn)
            return

    # Try as agent identity
    from space.os.spawn.api import agents

    agent = agents.get_agent(query)
    if agent:
        _list_agent_spawns(agent)
        return

    typer.echo(f"No spawn or agent found for: {query}", err=True)
    raise typer.Exit(1)


def _show_spawn_session(spawn):
    """Display full session log for a spawn."""
    if not spawn.session_id:
        typer.echo(f"Spawn {spawn.id} has no linked session_id", err=True)
        raise typer.Exit(1)

    # Find session file

    sessions_dir = paths.space_root() / ".space" / "sessions"
    session_path = None

    # Search provider subdirs for session file
    if sessions_dir.exists():
        for provider_dir in sessions_dir.iterdir():
            if not provider_dir.is_dir():
                continue
            candidate = provider_dir / f"{spawn.session_id}.jsonl"
            if candidate.exists():
                session_path = candidate
                break

    if not session_path or not session_path.exists():
        typer.echo(
            f"Session file not found for {spawn.session_id}. Run: sessions sync",
            err=True,
        )
        raise typer.Exit(1)

    # Display session metadata
    typer.echo()
    typer.echo(f"Spawn:       {spawn.id}")
    typer.echo(f"Agent:       {spawn.agent_id}")
    typer.echo(f"Status:      {spawn.status}")
    typer.echo(f"Session:     {spawn.session_id}")
    typer.echo(f"Created:     {spawn.created_at}")
    if spawn.ended_at:
        typer.echo(f"Ended:       {spawn.ended_at}")
    if spawn.channel_id:
        typer.echo(f"Channel:     {spawn.channel_id}")
    typer.echo()

    # Display session content (JSONL)
    try:
        with open(session_path) as f:
            line_count = sum(1 for _ in f)
        typer.echo(f"Session content ({line_count} messages):")
        typer.echo("-" * 60)

        with open(session_path) as f:
            for line in f:
                typer.echo(line.rstrip())
    except OSError as e:
        typer.echo(f"Error reading session file: {e}", err=True)
        raise typer.Exit(1) from None


def _list_agent_spawns(agent):
    """List all spawns for an agent."""
    from space.os.spawn.api import spawns

    agent_spawns = spawns.get_spawns_for_agent(agent.agent_id, limit=20)

    if not agent_spawns:
        typer.echo(f"No spawns found for agent: {agent.identity}")
        return

    typer.echo()
    typer.echo(f"Spawns for {agent.identity} (recent 20):")
    typer.echo()
    typer.echo(f"{'Spawn ID':<12} {'Status':<12} {'Session':<12} {'Created':<20}")
    typer.echo("-" * 56)

    for spawn in agent_spawns:
        session_id = spawn.session_id[:8] if spawn.session_id else "-"
        created = spawn.created_at.split("T")[0] if spawn.created_at else "-"
        typer.echo(f"{spawn.id[:12]:<12} {spawn.status:<12} {session_id:<12} {created:<20}")

    typer.echo()
    typer.echo("Run: sessions <spawn_id> to view full session log")


def main() -> None:
    """Entry point for sessions command."""
    try:
        sessions_app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e
