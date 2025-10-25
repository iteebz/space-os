"""Summary command."""

from dataclasses import asdict

import typer

from space.os.core import spawn
from space.os.lib import output

from .. import api
from . import app


@app.command("summary")
def summary(
    ctx: typer.Context,
    message: str = typer.Argument(
        None, help="The summary message. If provided, adds/replaces the summary."
    ),
    ident: str = typer.Option(None, "--as", help="Identity name"),
    include_archived: bool = typer.Option(False, "--archived", help="Include archived entries"),
):
    """Add, replace, or list summary entries for an identity."""
    ident = ident or ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent_id = spawn.ensure_agent(ident)

    if message:
        new_uuid = api.summary.update(agent_id, message, note="CLI summary update")
        output.out_text(f"Updated summary {new_uuid[-8:]}", ctx.obj)
    else:
        entries = api.summary.get(agent_id, limit=1)
        if not entries:
            output.out_text("No summary found", ctx.obj)
            return

        if ctx.obj.get("json_output"):
            typer.echo(output.out_json(asdict(entries[0])))
        else:
            output.out_text(f"CURRENT: [summary] {entries[0].message}", ctx.obj)
            chain = api.get_chain(entries[0].memory_id)
            if chain["predecessors"]:
                output.out_text("SUPERSEDES:", ctx.obj)
                for p in chain["predecessors"]:
                    output.out_text(f"  [{p.memory_id[-8:]}] {p.message}", ctx.obj)
