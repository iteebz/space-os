"""Bridge CLI - Clean command interface."""

import typer

from space.os import events
from space.os.lib import errors, output, readme

from . import api, export, messages, notes, utils
from .channels import app as channels_app
from .channels import archive as archive_cmd
from .channels import list_channels

errors.install_error_handler("bridge")

app = typer.Typer(invoke_without_command=True, add_help_option=False)


@app.callback()
def main_command(
    ctx: typer.Context,
    agent_id: str = typer.Option(None, "--as", help="Agent identity"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    """Bridge: AI Coordination Protocol"""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        _show_readme(ctx.obj)
        ctx.exit()

    if ctx.invoked_subcommand is None:
        if agent_id:
            ctx.invoke(
                messages.inbox,
                identity=agent_id,
                json_output=ctx.obj.get("json_output"),
                quiet_output=ctx.obj.get("quiet_output"),
            )
        else:
            _show_readme(ctx.obj)


app.add_typer(channels_app, name="channels")
app.command("send")(messages.send)
app.command("alert")(messages.alert)
app.command("recv")(messages.recv)
app.command("wait")(messages.wait)
app.command("inbox")(messages.inbox)
app.command("alerts")(messages.alerts)
app.command("notes")(notes.notes)
app.command("export")(export.export)
app.command("archive")(archive_cmd)
app.command("list")(list_channels)


def _show_readme(ctx_obj: dict):
    """Display bridge README."""
    content = readme.load("bridge")
    if content:
        typer.echo(content)
    else:
        output.out_text("BRIDGE: AI Coordination Protocol", ctx_obj)


def _print_active_channels(agent_id: str, json_output: bool, quiet_output: bool):
    """Render active channel list like the original dashboard."""
    try:
        active_channels = api.active_channels(agent_id=agent_id)
    except Exception as exc:
        if agent_id:
            events.emit(
                "bridge",
                "error",
                agent_id,
                output.out_json({"command": "list", "details": str(exc)}),
            )
        if not quiet_output:
            typer.echo(f"⚠️ Unable to load bridge channels: {exc}")
            typer.echo()
        return

    if not active_channels:
        if json_output:
            typer.echo(output.out_json([]))
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
        typer.echo(output.out_json(compact))
    elif not quiet_output:
        typer.echo("ACTIVE CHANNELS:")
        for channel in active_channels:
            last_activity, description = utils.format_channel_row(channel)
            typer.echo(f"  {last_activity}: {description}")
        typer.echo()


def main() -> None:
    """Entry point for poetry script."""
    app()
