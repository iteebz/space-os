import json
from dataclasses import asdict

import typer

from .. import api, utils

app = typer.Typer()


@app.command()
def history(
    identity: str = typer.Option(..., "--as", help="Agent identity to fetch history for"),
    limit: int | None = typer.Option(5, help="Limit results (weighted toward recent)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    preview: bool = typer.Option(False, "--preview", "-p", help="Show preview snapshot"),
):
    """Show all messages broadcast by identity across all channels."""
    try:
        messages = api.fetch_sender_history(identity, limit)
        if not messages:
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo(f"No messages from {identity}")
            return

        if json_output:
            typer.echo(json.dumps([asdict(msg) for msg in messages]))
        elif preview:
            typer.echo(f"📤 Last {len(messages)} sent by {identity}:")
            for msg in reversed(messages):
                prev = msg.content[:60].replace('\n', ' ')
                if len(msg.content) > 60:
                    prev += "..."
                typer.echo(f"  • {msg.channel_id}: {prev}")
        elif not quiet_output:
            typer.echo(f"--- Broadcast history for {identity} ({len(messages)} messages) ---")
            for msg in messages:
                timestamp = utils.format_local_time(msg.created_at)
                typer.echo(f"\n[{msg.channel_id} | {timestamp}]")
                typer.echo(msg.content)
    except Exception as exc:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        elif not quiet_output:
            typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc
