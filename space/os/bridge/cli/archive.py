"""Archive channels."""

from __future__ import annotations

import json

import typer

from space.os.bridge import ops

from .format import echo_if_output, output_json


def register(app: typer.Typer) -> None:
    @app.command()
    def archive(
        ctx: typer.Context,
        channels_arg: list[str] = typer.Argument(..., help="Channels to archive"),  # noqa: B008
        prefix: bool = typer.Option(False, "--prefix", help="Match by prefix"),
    ):
        """Archive channels."""
        try:
            names = channels_arg
            if prefix:
                chans = ops.list_channels()
                active = [c.name for c in chans if not c.archived_at]
                matched = []
                for pattern in channels_arg:
                    matched.extend([name for name in active if name.startswith(pattern)])
                names = list(set(matched))

            results = []
            for name in names:
                try:
                    ops.archive_channel(name)
                    results.append({"channel": name, "status": "archived"})
                    echo_if_output(f"Archived channel: {name}", ctx)
                except ValueError:
                    results.append(
                        {
                            "channel": name,
                            "status": "error",
                            "message": f"Channel '{name}' not found.",
                        }
                    )
                    echo_if_output(f"❌ Channel '{name}' not found.", ctx)
            if ctx.obj.get("json_output"):
                typer.echo(json.dumps(results))
        except Exception as e:
            output_json({"status": "error", "message": str(e)}, ctx) or echo_if_output(
                f"❌ {e}", ctx
            )
            raise typer.Exit(code=1) from e
