"""Display formatting for trace results."""

import typer

from space.lib import format as fmt


def display_agent_trace(result: dict) -> None:
    """Display agent identity trace: recent spawns."""
    typer.echo(f"\nTrace: {result['identity']}\n")

    spawns = result.get("recent_spawns", [])
    if not spawns:
        typer.echo("No spawns found")
        return

    for spawn in spawns:
        short_id = spawn["short_id"]
        status = spawn["status"]
        started = fmt.humanize_timestamp(spawn["started_at"])
        duration = spawn["duration_seconds"]

        status_marker = "✓" if status == "COMPLETED" else "✗"
        duration_str = f"{duration:.0f}s" if duration else "running"

        typer.echo(f"{status_marker} {short_id} ({started}) {duration_str}")

        if spawn["outcome"]:
            typer.echo(f"  {spawn['outcome']}")
        typer.echo()


def display_session_trace(result: dict) -> None:
    """Display spawn/session trace: execution context."""
    spawn_id = result.get("spawn_id") or result.get("short_id", "?")
    identity = result["identity"]
    status = result["status"].lower()

    status_marker = "✓" if "complet" in status else "✗"
    typer.echo(f"\n{status_marker} Spawn {spawn_id} ({identity})\n")

    if result.get("created_at"):
        typer.echo(f"Created: {fmt.humanize_timestamp(result['created_at'])}")

    if result.get("started_at"):
        typer.echo(f"Started: {fmt.humanize_timestamp(result['started_at'])}")

    if result.get("ended_at"):
        typer.echo(f"Ended: {fmt.humanize_timestamp(result['ended_at'])}")

    if result.get("duration_seconds"):
        typer.echo(f"Duration: {result['duration_seconds']:.1f}s")

    if result.get("triggered_by"):
        typer.echo(f"Triggered by: {result['triggered_by']}")

    if result.get("session_id"):
        typer.echo(f"Session: {result['session_id'][:8]}")

    if result.get("channel_id"):
        typer.echo(f"Channel: #{result['channel_id'][:8]}")

    typer.echo()

    if result.get("channel_context"):
        ctx = result["channel_context"]
        typer.echo("Context (last message before spawn):")
        typer.echo(f"  {ctx['content'][:80]}")
        typer.echo()

    if result.get("input"):
        typer.echo("Input (task/prompt):")
        typer.echo(f"  {result['input'][:100]}")
        typer.echo()

    if result.get("output"):
        typer.echo("Output:")
        typer.echo(f"  {result['output'][:120]}")
        typer.echo()

    if result.get("stderr"):
        typer.echo("Error:")
        typer.echo(f"  {result['stderr'][:120]}")
        typer.echo()

    if result.get("last_memory_mutation"):
        mem = result["last_memory_mutation"]
        typer.echo(f"Memory written: [{mem['topic']}] {mem['message'][:80]}")
        typer.echo()


def display_channel_trace(result: dict) -> None:
    """Display channel trace: active agents."""
    typer.echo(f"\nChannel: #{result['channel_name']}\n")

    participants = result.get("participants", [])
    if not participants:
        typer.echo("No activity in this channel")
        return

    for p in participants:
        identity = p["identity"]
        last_at = (
            fmt.humanize_timestamp(p["last_message_at"]) if p["last_message_at"] else "unknown"
        )
        typer.echo(f"  {identity} (last: {last_at})")
        if p.get("last_message"):
            typer.echo(f'    "{p["last_message"]}"')
        typer.echo()
