"""Bridge CLI - Clean command interface."""

import json

import typer

from space import events
from space.lib import errors
from space.spawn import registry
from space.lib.cli_utils import common_cli_options

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

errors.install_error_handler("bridge")

app = typer.Typer(invoke_without_command=True, add_help_option=False)


@app.callback()
@common_cli_options
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
):
    """Bridge: AI Coordination Protocol"""
    if help_flag:
        typer.echo("Bridge CLI - A command-line interface for Bridge.")
        typer.echo()
        typer.echo(ctx.command.get_help(ctx))
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        if agent_id:
            ctx.invoke(
                recv_cmds.inbox,
                identity=agent_id,
                json_output=ctx.obj.get("json_output"),
                quiet_output=ctx.obj.get("quiet_output"),
            )
        else:
            if not ctx.obj.get("quiet_output"):
                typer.echo("Bridge CLI - A command-line interface for Bridge.")
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
@common_cli_options
def list(
    ctx: typer.Context,
    agent_id: str = typer.Option(None, "--as", help="Agent identity"),
):
    """List all active channels."""
    if agent_id:
        agent_id = registry.ensure_agent(agent_id)
        events.emit("bridge", "list_active_channels", agent_id, "")
    _print_active_channels(
        agent_id, ctx.obj.get("json_output"), ctx.obj.get("quiet_output")
    )


def _print_active_channels(agent_id: str, json_output: bool, quiet_output: bool):
    """Render active channel list like the original dashboard."""
    try:
        active_channels = api.active_channels(agent_id=agent_id)
    except Exception as exc:  # pragma: no cover - defensive logging for CLI usage
        if agent_id:
            events.emit(
                "bridge",
                "error",
                agent_id,
                json.dumps({"command": "list", "details": str(exc)}),
            )
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
