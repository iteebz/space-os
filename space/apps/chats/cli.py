"""Chat CLI commands."""

import typer

from space.apps.chats import api
from space.lib import paths

app = typer.Typer()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(stats)


@app.command()
def sync():
    """Sync chats from ~/.claude, ~/.codex, ~/.gemini to ~/.space/chats/."""
    results = api.sync_all_providers()

    typer.echo("✓ Chat sync complete")
    typer.echo()
    typer.echo(f"{'Provider':<10} {'Discovered':<12} {'Synced'}")
    typer.echo("-" * 40)

    total_discovered = 0
    total_synced = 0

    for provider in ("claude", "codex", "gemini"):
        discovered, synced = results.get(provider, (0, 0))
        total_discovered += discovered
        total_synced += synced
        status = "✓" if synced > 0 else "-"
        typer.echo(f"{provider:<10} {discovered:<12} {synced:<12} {status}")

    typer.echo("-" * 40)
    typer.echo(f"{'TOTAL':<10} {total_discovered:<12} {total_synced}")


@app.command()
def stats():
    """Show chat statistics across providers."""
    provider_stats = api.get_provider_stats()

    if not provider_stats:
        typer.echo("No chats synced yet. Run: space chats sync")
        return

    typer.echo("Chat statistics:")
    typer.echo()
    typer.echo(f"{'Provider':<12} {'Sessions':<12} {'Size (MB)'}")
    typer.echo("-" * 40)

    total_files = 0
    total_size = 0

    for provider in sorted(provider_stats.keys()):
        stats_dict = provider_stats[provider]
        total_files += stats_dict["files"]
        total_size += stats_dict["size_mb"]
        typer.echo(f"{provider:<12} {stats_dict['files']:<12} {stats_dict['size_mb']:>10.1f}")

    typer.echo("-" * 40)
    typer.echo(f"{'TOTAL':<12} {total_files:<12} {total_size:>10.1f}")
    typer.echo()
    typer.echo(f"Location: {paths.chats_dir()}")
