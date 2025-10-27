"""Show active channels."""

from __future__ import annotations

import typer

from space.os.bridge import ops

from .format import echo_if_output, format_channel_row, output_json, should_output


def register(app: typer.Typer) -> None:
    @app.command()
    def channels(
        ctx: typer.Context,
        all: bool = typer.Option(False, "--all", help="Include archived channels"),
    ):
        """Show active channels."""
        try:
            chans = ops.list_channels(all=all)

            if not chans:
                output_json([], ctx) or echo_if_output("No channels found", ctx)
                return

            if output_json(
                [
                    {
                        "name": c.name,
                        "topic": c.topic,
                        "message_count": c.message_count,
                        "last_activity": c.last_activity,
                        "unread_count": c.unread_count,
                        "archived_at": c.archived_at,
                    }
                    for c in chans
                ],
                ctx,
            ):
                return

            active = [c for c in chans if not c.archived_at]
            archived = [c for c in chans if c.archived_at]
            active.sort(key=lambda t: t.name)
            archived.sort(key=lambda t: t.name)

            if not should_output(ctx):
                return

            if active:
                echo_if_output(f"ACTIVE CHANNELS ({len(active)}):", ctx)
                for channel in active:
                    last_activity, description = format_channel_row(channel)
                    echo_if_output(f"  {last_activity}: {description}", ctx)

            if all and archived:
                echo_if_output(f"\nARCHIVED ({len(archived)}):", ctx)
                for channel in archived:
                    last_activity, description = format_channel_row(channel)
                    echo_if_output(f"  {last_activity}: {description}", ctx)
        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
