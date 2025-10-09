import base64
import binascii
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Annotated

import typer

from space.lib import formatters, protocols

from .. import events
from . import db, utils

app = typer.Typer(invoke_without_command=True, add_help_option=False)
channels_app = typer.Typer(invoke_without_command=True)
messages_app = typer.Typer()


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
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Bridge: AI Coordination Protocol"""
    if help_flag:
        try:
            typer.echo(protocols.load("bridge"))
            typer.echo()
        except FileNotFoundError:
            typer.echo("❌ bridge.md protocol not found")
            typer.echo()
        typer.echo(ctx.command.get_help(ctx))
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        _print_active_channels(json_output, quiet_output)
        if not quiet_output:
            try:
                typer.echo(protocols.load("bridge"))
            except FileNotFoundError:
                typer.echo("❌ bridge.md protocol not found")
            else:
                typer.echo()


def _print_active_channels(json_output: bool, quiet_output: bool):
    try:
        channels = db.fetch_channels(None, time_filter="-7 days")
        channels.sort(key=lambda t: t.last_activity if t.last_activity else "", reverse=True)
        active_channels = channels
    except Exception as exc:
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
        typer.echo(json.dumps([asdict(channel) for channel in active_channels]))
    elif not quiet_output:
        typer.echo("ACTIVE CHANNELS:")
        for channel in active_channels:
            last_activity, description = formatters.format_channel_row(channel)
            typer.echo(f"  {last_activity}: {description}")
        typer.echo()


@channels_app.callback()
def channels_root(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        list_channels()


@channels_app.command("list")
def list_channels(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    all_channels = db.fetch_channels(None)

    if not all_channels:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No channels found")
        return

    if json_output:
        typer.echo(json.dumps([asdict(channel) for channel in all_channels]))
        return

    active_channels = []
    archived_channels = []

    archived_threshold = datetime.now() - timedelta(days=29)

    for channel in all_channels:
        created_at_dt = datetime.fromisoformat(channel.created_at)
        if created_at_dt < archived_threshold:
            archived_channels.append(channel)
        else:
            active_channels.append(channel)
    active_channels.sort(key=lambda t: t.name)
    archived_channels.sort(key=lambda t: t.name)

    if not quiet_output:
        typer.echo("--- Active Channels ---")

        for channel in active_channels:
            last_activity, description = formatters.format_channel_row(channel)
            typer.echo(f"{last_activity}: {description}")

        if archived_channels:
            typer.echo("\n--- Archived Channels ---")
            for channel in archived_channels:
                last_activity, description = formatters.format_channel_row(channel)
                typer.echo(f"{last_activity}: {description}")


@channels_app.command()
def create(
    channel_name: str = typer.Argument(..., help="The name of the channel to create."),
    topic: Annotated[str, typer.Option(..., help="The initial topic for the channel.")] = None,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        channel_id = db.create_channel(channel_name, topic)
        if json_output:
            typer.echo(
                json.dumps(
                    {"status": "success", "channel_name": channel_name, "channel_id": channel_id}
                )
            )
        elif not quiet_output:
            typer.echo(f"Created channel: {channel_name} (ID: {channel_id})")
    except ValueError as e:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(e)}))
        elif not quiet_output:
            typer.echo(f"❌ Error creating channel: {e}")


@channels_app.command()
def archive(
    channels: Annotated[list[str], typer.Argument(...)],
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    results = []
    for channel_name in channels:
        try:
            channel_id = db.get_channel_id(channel_name)
            db.archive_channel(channel_id)
            if json_output:
                results.append({"channel": channel_name, "status": "archived"})
            elif not quiet_output:
                typer.echo(f"Archived channel: {channel_name}")
        except ValueError:
            if json_output:
                results.append(
                    {
                        "channel": channel_name,
                        "status": "error",
                        "message": f"Channel '{channel_name}' not found.",
                    }
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel_name}' not found.")
    if json_output:
        typer.echo(json.dumps(results))


@channels_app.command()
def delete(
    channel: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        channel_id = db.get_channel_id(channel)
        db.delete_channel(channel_id)
        if json_output:
            typer.echo(json.dumps({"status": "deleted", "channel": channel}))
        elif not quiet_output:
            typer.echo(f"Deleted channel: {channel}")
    except ValueError:
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")


@app.command()
def send(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option("human", "--as", help="Identity (defaults to human)"),
    decode_base64: bool = typer.Option(False, "--base64", help="Decode base64 payload"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    if decode_base64:
        try:
            payload = base64.b64decode(content, validate=True)
            content = payload.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            if json_output:
                typer.echo(json.dumps({"status": "error", "message": "Invalid base64 payload"}))
            else:
                raise typer.BadParameter("Invalid base64 payload", param_hint="content") from exc

    try:
        events.emit(
            "bridge",
            "message_sending",
            identity,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        try:
            channel_id = db.get_channel_id(channel)
        except Exception:
            channel_id = db.create_channel(channel)
        db.get_channel_name(channel_id)
        db.create_message(channel_id, identity, content)
        events.emit(
            "bridge",
            "message_sent",
            identity,
            json.dumps({"channel": channel, "identity": identity}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "success", "channel": channel, "identity": identity}))
        elif not quiet_output:
            typer.echo(
                f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}"
            )
    except ValueError as exc:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "send", "details": str(exc)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from exc


@app.command()
def alert(
    channel: str = typer.Argument(...),
    content: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Identity sending alert"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        events.emit(
            "bridge",
            "alert_triggering",
            identity,
            json.dumps({"channel": channel, "identity": identity, "content": content}),
        )
        try:
            channel_id = db.get_channel_id(channel)
        except Exception:
            channel_id = db.create_channel(channel)
        db.get_channel_name(channel_id)
        db.create_message(channel_id, identity, content, priority="alert")
        events.emit(
            "bridge",
            "alert_triggered",
            identity,
            json.dumps({"channel": channel, "identity": identity}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "success", "channel": channel, "identity": identity}))
        elif not quiet_output:
            typer.echo(f"Alert sent to {channel} as {identity}")
    except ValueError as exc:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "alert", "details": str(exc)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from exc


@app.command()
def notes(
    channel: str = typer.Argument(...),
    content: str | None = typer.Argument(None),
    identity: str | None = typer.Option(
        None, "--as", help="Your agent identity (claude/gemini/codex)"
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    if content is None:
        try:
            channel_id = db.get_channel_id(channel)
            notes = db.get_notes(channel_id)
            if not notes:
                if json_output:
                    typer.echo(json.dumps([]))
                elif not quiet_output:
                    typer.echo(f"No notes for channel: {channel}")
                return

            if json_output:
                typer.echo(json.dumps(notes))
            elif not quiet_output:
                typer.echo(f"Notes for {channel}:")
                for note in notes:
                    timestamp = utils.format_local_time(note["created_at"])
                    typer.echo(f"[{timestamp}] {note['author']}: {note['content']}")
                    typer.echo()
        except ValueError as e:
            if json_output:
                typer.echo(
                    json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found.")
            raise typer.Exit(code=1) from e
    else:
        if not identity:
            if json_output:
                typer.echo(
                    json.dumps(
                        {
                            "status": "error",
                            "message": "Must specify --as identity when adding notes",
                        }
                    )
                )
            elif not quiet_output:
                typer.echo("❌ Must specify --as identity when adding notes")
            raise typer.Exit(code=1)
        try:
            channel_id = db.get_channel_id(channel)
            db.create_note(channel_id, identity, content)
            if json_output:
                typer.echo(
                    json.dumps({"status": "success", "channel": channel, "identity": identity})
                )
            elif not quiet_output:
                typer.echo(f"Added note to {channel}")
        except ValueError as e:
            if json_output:
                typer.echo(
                    json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
                )
            elif not quiet_output:
                typer.echo(f"❌ Channel '{channel}' not found.")
            raise typer.Exit(code=1) from e


@app.command()
def recv(
    channel: str = typer.Argument(...),
    identity: str = typer.Option(..., "--as", help="Agent identity to receive as"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        events.emit(
            "bridge",
            "messages_receiving",
            identity,
            json.dumps({"channel": channel, "identity": identity}),
        )
        try:
            channel_id = db.get_channel_id(channel)
        except Exception:
            channel_id = db.create_channel(channel)
        messages = db.get_new_messages(channel_id, identity)
        if messages:
            db.set_bookmark(identity, channel_id, messages[-1].id)
        count = len(messages)
        context = db.get_topic(channel_id)
        participants = db.get_participants(channel_id)
        if json_output:
            typer.echo(
                json.dumps(
                    {
                        "messages": [asdict(msg) for msg in messages],
                        "count": count,
                        "context": context,
                        "participants": participants,
                    }
                )
            )
        elif not quiet_output:
            for msg in messages:
                events.emit(
                    "bridge",
                    "message_received",
                    identity,
                    json.dumps(
                        {
                            "channel": channel,
                            "identity": identity,
                            "sender_id": msg.sender,
                            "content": msg.content,
                        }
                    ),
                )
                typer.echo(f"[{msg.sender}] {msg.content}")
                typer.echo()
    except ValueError as e:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "recv", "details": str(e)}),
        )
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from e


@app.command()
def export(
    channel: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        channel_id = db.get_channel_id(channel)
        data = db.get_export_data(channel_id)

        if json_output:
            export_data = {
                "channel_name": data.channel_name,
                "topic": data.topic,
                "participants": data.participants,
                "message_count": data.message_count,
                "created_at": data.created_at,
                "messages": [asdict(msg) for msg in data.messages],
                "notes": [asdict(note) for note in data.notes],
            }
            typer.echo(json.dumps(export_data))
        elif not quiet_output:
            typer.echo(f"# {data.channel_name}")
            typer.echo()
            if data.topic:
                typer.echo(f"Topic: {data.topic}")
                typer.echo()
            typer.echo(f"Participants: {', '.join(data.participants)}")
            typer.echo(f"Messages: {data.message_count}")

            if data.created_at:
                created = datetime.fromisoformat(data.created_at)
                typer.echo(f"Created: {created.strftime('%Y-%m-%d')}")

            typer.echo()
            typer.echo("---")
            typer.echo()

            combined = []
            for msg in data.messages:
                combined.append(("msg", msg))
            for note in data.notes:
                combined.append(("note", note))

            combined.sort(key=lambda x: x[1].created_at)

            for item_type, item in combined:
                created = datetime.fromisoformat(item.created_at)
                timestamp = created.strftime("%Y-%m-%d %H:%M:%S")

                if item_type == "msg":
                    typer.echo(f"[{item.sender} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()
                else:
                    typer.echo(f"[NOTE: {item.author} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()

    except ValueError as e:
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found.")
        raise typer.Exit(code=1) from e


@messages_app.command()
def alerts(
    identity: str = typer.Option(..., "--as", help="Agent identity to check alerts for"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        events.emit("bridge", "alerts_checking", identity, json.dumps({"identity": identity}))
        alert_messages = db.get_alerts(identity)
        events.emit(
            "bridge",
            "alerts_checked",
            identity,
            json.dumps({"identity": identity, "count": len(alert_messages)}),
        )
        if not alert_messages:
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo(f"No alerts for {identity}")
            return

        if json_output:
            typer.echo(json.dumps([asdict(msg) for msg in alert_messages]))
        elif not quiet_output:
            typer.echo(f"--- Alerts for {identity} ({len(alert_messages)} unread) ---")
            for msg in alert_messages:
                typer.echo(f"\n[{msg.sender} | {msg.channel_id}]")
                typer.echo(msg.content)
    except Exception as exc:
        events.emit(
            "bridge",
            "error_occurred",
            identity,
            json.dumps({"command": "alerts", "details": str(exc)}),
        )
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        elif not quiet_output:
            typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@messages_app.command()
def history(
    identity: str = typer.Option(..., "--as", help="Agent identity to fetch history for"),
    limit: int | None = typer.Option(None, help="Limit results (weighted toward recent)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    try:
        messages = db.get_sender_history(identity, limit)
        if not messages:
            if json_output:
                typer.echo(json.dumps([]))
            elif not quiet_output:
                typer.echo(f"No messages from {identity}")
            return

        if json_output:
            typer.echo(json.dumps([asdict(msg) for msg in messages]))
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


app.add_typer(channels_app, name="channels")
app.add_typer(messages_app, name="messages")


def main() -> None:
    app()
