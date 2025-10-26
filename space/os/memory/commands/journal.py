"""Journal command."""

from dataclasses import asdict

import typer

from space.lib import output
from space.os import spawn

from .. import api
from . import app


@app.command("journal")
def journal(
    ctx: typer.Context,
    message: str = typer.Argument(
        None, help="The journal message. If provided, adds/replaces the journal."
    ),
    ident: str = typer.Option(None, "--as", help="Identity name"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """Add, replace, or list journal entries for an identity."""
    ident = ident or ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(ident)
    if not agent:
        raise typer.BadParameter(f"Identity '{ident}' not registered.")
    agent_id = agent.agent_id

    if message:
        existing = api.list_entries(ident, topic="journal", limit=1)
        if existing:
            new_uuid = api.replace_entry([existing[0].memory_id], agent_id, "journal", message)
        else:
            new_uuid = api.add_entry(agent_id, "journal", message)
        output.out_text(f"Updated journal {new_uuid[-8:]}", ctx.obj)
    else:
        entries = api.list_entries(ident, topic="journal", limit=1)
        if not entries:
            output.out_text("No journal found", ctx.obj)
            return

        if ctx.obj.get("json_output"):
            typer.echo(output.out_json(asdict(entries[0])))
        else:
            output.out_text(f"CURRENT: [journal] {entries[0].message}", ctx.obj)
            chain = api.get_chain(entries[0].memory_id)
            if chain["predecessors"]:
                output.out_text("SUPERSEDES:", ctx.obj)
                for p in chain["predecessors"]:
                    output.out_text(f"  [{p.memory_id[-8:]}] {p.message}", ctx.obj)
