"""Export command."""

import json
from dataclasses import asdict
from datetime import datetime

import typer

from space.core import spawn

from ..api import channels
from ..api import export as ex


def _display_name(agent_id: str) -> str:
    agent = spawn.get_agent(agent_id)
    return agent.identity if agent else agent_id


def export_cmd(
    ctx: typer.Context,
    channel: str,
    identity: str | None = None,
):
    """Export channel transcript."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    if identity and isinstance(identity, str):  # identity optional for plain exports
        agent = spawn.get_agent(identity)
        if not agent:
            raise typer.Exit(f"Identity '{identity}' not registered.")
    try:
        channel_id = channels.resolve_channel(channel).channel_id
        data = ex.get_export_data(channel_id)

        if json_output:
            export_data_dict = asdict(data)
            export_data_dict["members"] = [_display_name(p) for p in data.members]
            for msg in export_data_dict["messages"]:
                msg["agent_id"] = _display_name(msg["agent_id"])
            for note in export_data_dict["notes"]:
                note["agent_id"] = _display_name(note["agent_id"])
            typer.echo(json.dumps(export_data_dict, indent=2))
        elif not quiet_output:
            typer.echo(f"# {data.channel_name}")
            typer.echo()
            if data.topic:
                typer.echo(f"Topic: {data.topic}")
                typer.echo()
            participant_names = [_display_name(p) for p in data.members]
            typer.echo(f"Participants: {', '.join(participant_names)}")
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
                    sender_name = _display_name(item.agent_id)
                    typer.echo(f"[{sender_name} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()
                else:
                    author_name = _display_name(item.agent_id)
                    typer.echo(f"[NOTE: {author_name} | {timestamp}]")
                    typer.echo(item.content)
                    typer.echo()

    except ValueError as e:
        if json_output:
            typer.echo(
                json.dumps({"status": "error", "message": f"Channel '{channel}' not found."})
            )
        elif not quiet_output:
            typer.echo(f"❌ Channel '{channel}' not found. Run `bridge` to list channels.")
        raise typer.Exit(code=1) from e
