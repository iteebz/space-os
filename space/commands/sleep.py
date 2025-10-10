"""Sleep command: pre-compaction hygiene."""

import json
import subprocess

import typer

SLEEP_CHECKLIST = """
✓ Before you go:
  1. Extract signal → memory/knowledge
  2. Archive stale entries
  3. Mark channels read: bridge recv <channel> --as <identity>
  4. Log blockers
  5. Reflect: bridge send space-feedback <reflection> --as <identity>

💀 Clean death. Next self thanks you.
"""


def _get_git_status() -> str | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
            cwd=".",
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def sleep(
    identity: str = typer.Option(..., "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Prepare for death. Clean context for your next self."""
    from .. import events
    from ..bridge.api import channels as bridge_channels
    from ..memory import db as memory_db

    events.identify(identity, "sleep")

    if not quiet:
        typer.echo(f"Running sleep for {identity}...")

    channels = bridge_channels.inbox_channels(identity)
    active = [ch.name for ch in channels[:5]]

    if not quiet and active:
        typer.echo(f"\n📬 {len(active)} active channels:")
        for ch in active:
            typer.echo(f"  • {ch}")
            memory_db.add_checkpoint_entry(
                identity=identity,
                topic="bridge-context",
                message=f"Active channel: {ch}",
                bridge_channel=ch,
            )

    memory_count = len(memory_db.get_entries(identity))
    git_status = _get_git_status()

    if git_status:
        memory_db.add_checkpoint_entry(
            identity=identity,
            topic="git-status",
            message="Uncommitted changes detected.",
            code_anchors=git_status,
        )
        if not quiet:
            typer.echo(f"\n⚠️ Uncommitted changes detected:\n{git_status}")

    if memory_count == 0:
        memory_db.add_checkpoint_entry(
            identity=identity,
            topic="memory-gap",
            message="No memory entries found for this identity.",
        )
        if not quiet:
            typer.echo(f"\n🧠 No memory entries found for {identity}. Possible memory gap.")

    if not quiet:
        typer.echo(f"\n🧠 {memory_count} memory entries")

        typer.echo("\n--- Pre-compaction Summary ---")
        typer.echo(f"Active Channels: {len(active)}")
        if git_status:
            typer.echo("Uncommitted Git Changes: Yes")
        else:
            typer.echo("Uncommitted Git Changes: No")
        if memory_count == 0:
            typer.echo("Memory Gap Detected: Yes")
        else:
            typer.echo("Memory Gap Detected: No")
        typer.echo("------------------------------")

        typer.echo(SLEEP_CHECKLIST)

    if json_output:
        typer.echo(
            json.dumps(
                {"identity": identity, "active_channels": active, "memory_entries": memory_count}
            )
        )
