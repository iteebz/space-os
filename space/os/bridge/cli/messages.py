"""Message subcommand app: send, recv, wait, inbox."""

from dataclasses import asdict

import typer

from space.os import spawn
from space.os.bridge import ops

from .format import echo_if_output, format_channel_row, output_json, should_output

app = typer.Typer(help="Send and receive messages")


@app.command("send")
def send_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Target channel"),
    content: str = typer.Argument(..., help="Message content"),
    identity: str = typer.Option("human", "--as", help="Sender identity"),
    decode_base64: bool = typer.Option(False, "--base64", help="Treat content as base64"),
):
    """Send a message to a channel."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        ops.send_message(channel, identity, content, decode_base64)
        output_json(
            {"status": "success", "channel": channel, "identity": identity}, ctx
        ) or echo_if_output(
            f"Sent to {channel}" if identity == "human" else f"Sent to {channel} as {identity}", ctx
        )
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("recv")
def recv_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to read from"),
    identity: str = typer.Option(..., "--as", help="Receiver identity"),
):
    """Receive unread messages from a channel."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        msgs, count, context, participants = ops.recv_messages(channel, agent.agent_id)

        output_json(
            {
                "messages": [asdict(msg) for msg in msgs],
                "count": count,
                "context": context,
                "participants": participants,
            },
            ctx,
        ) or None
        if should_output(ctx):
            for msg in msgs:
                sender = spawn.get_agent(msg.agent_id)
                sender_name = sender.identity if sender else msg.agent_id[:8]
                echo_if_output(f"[{sender_name}] {msg.content}", ctx)
                echo_if_output("", ctx)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("wait")
def wait_cmd(
    ctx: typer.Context,
    channel: str = typer.Argument(..., help="Channel to monitor"),
    identity: str = typer.Option(..., "--as", help="Receiver identity"),
    poll_interval: float = typer.Option(0.1, "--interval", help="Poll interval in seconds"),
):
    """Block and wait for a new message in a channel."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        other_messages, count, context, participants = ops.wait_for_message(
            channel, agent.agent_id, poll_interval
        )
        output_json(
            {
                "messages": [asdict(msg) for msg in other_messages],
                "count": count,
                "context": context,
                "participants": participants,
            },
            ctx,
        ) or None
        if should_output(ctx):
            for msg in other_messages:
                sender = spawn.get_agent(msg.agent_id)
                sender_name = sender.identity if sender else msg.agent_id[:8]
                echo_if_output(f"[{sender_name}] {msg.content}", ctx)
                echo_if_output("", ctx)
    except ValueError as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e
    except KeyboardInterrupt:
        echo_if_output("\n", ctx)
        raise typer.Exit(code=0) from None
    except Exception as e:
        output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(f"❌ {e}", ctx)
        raise typer.Exit(code=1) from e


@app.command("inbox")
def inbox_cmd(
    ctx: typer.Context,
    identity: str = typer.Option(..., "--as", help="Agent identity"),
):
    """Show channels with unread messages."""
    try:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Identity '{identity}' not registered.")
        chans = ops.fetch_inbox(agent.agent_id)
        if not chans:
            output_json([], ctx) or echo_if_output("Inbox empty", ctx)
            return

        output_json([asdict(c) for c in chans], ctx) or None
        if should_output(ctx):
            for channel in chans:
                last_activity, description = format_channel_row(channel)
                echo_if_output(f"  {last_activity}: {description}", ctx)
    except Exception as exc:
        output_json({"status": "error", "message": str(exc)}, ctx) or echo_if_output(
            f"❌ {exc}", ctx
        )
        raise typer.Exit(code=1) from exc
