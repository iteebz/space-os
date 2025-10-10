"""Bridge CLI - Clean command interface."""

import json

import typer

from space.lib import readme

from . import api, utils
from .commands import (
    export as export_cmds,
)
from .commands import (
    history as history_cmds,
)
from .commands import (
    notes as notes_cmds,
)
from .commands import (
    recv as recv_cmds,
)
from .commands import (
    send as send_cmds,
)
from .commands.channels import app as channels_app
from .commands.channels import archive as archive_cmd
from .commands.monitor import app as monitor_app

app = typer.Typer(invoke_without_command=True, add_help_option=False)


@app.callback()
def main_command(
    ctx: typer.Context,
    help_flag: bool = typer.Option(
        False,
        "--help",
        "-h",
        help="Show protocol instructions and command overview.",
        is_eager=True,
    ),
    agent_id: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Bridge: AI Coordination Protocol"""
    if help_flag:
        try:
            typer.echo(readme.load("bridge"))
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ bridge README not found: {e}")
            typer.echo()
        typer.echo(ctx.command.get_help(ctx))
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        if agent_id:
            ctx.invoke(
                recv_cmds.inbox,
                identity=agent_id,
                json_output=json_output,
                quiet_output=quiet_output,
            )
        else:
            if not quiet_output:
                try:
                    typer.echo(readme.load("bridge"))
                except (FileNotFoundError, ValueError) as e:
                    typer.echo(f"❌ bridge README not found: {e}")
                else:
                    typer.echo()


app.add_typer(channels_app, name="channels")
app.add_typer(monitor_app, name="monitor")
app.command("send")(send_cmds.send)
app.command("alert")(send_cmds.alert)
app.command("recv")(recv_cmds.recv)
app.command("inbox")(recv_cmds.inbox)
app.command("alerts")(recv_cmds.alerts)
app.command("notes")(notes_cmds.notes)
app.command("export")(export_cmds.export)
app.command("history")(history_cmds.history)
app.command("archive")(archive_cmd)


@app.command()
def list(
    agent_id: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """List all active channels."""
    if agent_id:
        from space.spawn import registry
        agent_id = registry.ensure_agent(agent_id)
    _print_active_channels(agent_id, json_output, quiet_output)


def _print_active_channels(agent_id: str, json_output: bool, quiet_output: bool):
    """Render active channel list like the original dashboard."""
    try:
        active_channels = api.active_channels(agent_id=agent_id)
    except Exception as exc:  # pragma: no cover - defensive logging for CLI usage
        if not quiet_output:
            typer.echo(f"⚠️ Unable to load bridge channels: {exc}")
            typer.echo()
        return

    if not active_channels:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No active bridge channels yet.")
            typer.echo()
        return

    if json_output:
        compact = [
            {
                "name": c.name,
                "topic": c.topic,
                "message_count": c.message_count,
                "last_activity": c.last_activity,
                "unread_count": c.unread_count,
            }
            for c in active_channels
        ]
        typer.echo(json.dumps(compact, indent=2))
    elif not quiet_output:
        typer.echo("ACTIVE CHANNELS:")
        for channel in active_channels:
            last_activity, description = utils.format_channel_row(channel)
            typer.echo(f"  {last_activity}: {description}")
        typer.echo()


def main() -> None:
    """Entry point for poetry script."""
    app()
