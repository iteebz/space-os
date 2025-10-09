"""Handover CLI - Pre-compaction hygiene protocol."""

import typer

from space.bridge.api import channels as bridge_channels
from space.lib import lattice
from space.memory import db as memory_db

app = typer.Typer(invoke_without_command=True, add_help_option=False)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    help_flag: bool = typer.Option(
        False,
        "--help",
        "-h",
        help="Show handover protocol instructions.",
        is_eager=True,
    ),
    identity: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Pass clean context to next self across death boundary."""
    if help_flag:
        try:
            protocol = lattice.load("# handover")
            typer.echo(protocol)
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ Protocol not found: {e}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        if not identity:
            typer.echo("❌ --as <identity> required")
            raise typer.Exit(code=1)

        run_handover(identity, json_output, quiet_output)
        raise typer.Exit()

    ctx.obj = {"identity": identity, "json_output": json_output, "quiet_output": quiet_output}


def run_handover(identity: str, json_output: bool, quiet_output: bool):
    """Execute handover protocol."""
    if not quiet_output:
        typer.echo(f"Running handover for {identity}...")

    # Get active channels with unreads
    channels = bridge_channels.inbox_channels(identity)
    active_channel_names = [ch.name for ch in channels[:5]]

    if not quiet_output and active_channel_names:
        typer.echo(f"\n📬 {len(active_channel_names)} active channels with unreads:")
        for ch_name in active_channel_names:
            typer.echo(f"  • {ch_name}")

    # Get memory count
    memory_entries = memory_db.get_entries(identity)
    memory_count = len(memory_entries)

    if not quiet_output:
        typer.echo(f"\n🧠 {memory_count} memory entries")

    # Checklist
    if not quiet_output:
        typer.echo("\n✓ Handover checklist:")
        typer.echo("  1. Extract inbox signal → memory/knowledge")
        typer.echo("  2. Prune stale memory (keep active context only)")
        typer.echo("  3. Mark channels read: bridge recv <channel> --as <identity>")
        typer.echo("  4. Log open blockers to memory")
        typer.echo("\n💀 Ready for clean death.")

    if json_output:
        import json

        typer.echo(
            json.dumps(
                {
                    "identity": identity,
                    "active_channels": active_channel_names,
                    "memory_entries": memory_count,
                }
            )
        )
