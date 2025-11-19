"""Knowledge CLI: Domain-specific Knowledge Base."""

from dataclasses import asdict
from typing import Annotated

import typer

from space.cli import argv, output
from space.cli.errors import error_feedback
from space.os import spawn
from space.os.knowledge import api

argv.flex_args("as")

app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    identity: Annotated[str | None, typer.Option("--as", help="Agent identity to use.")] = None,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Contribute to shared truth. Once written, entries are immutable.
    Archive if wrong, add new if refined. Your insights compound collective intelligence."""
    output.init_context(ctx, json_output, quiet_output, identity)

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("add")
@error_feedback
def add(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain path (e.g., architecture/caching/redis)"),
    content: str = typer.Argument(..., help="The knowledge content"),
):
    """Add knowledge to a domain path.

    Example:
      knowledge add architecture/caching/redis "Redis uses single thread for consistency" --as sentinel
    """
    from space.lib.paths import validate_domain_path

    contributor = ctx.obj.get("identity")
    if not contributor:
        raise typer.BadParameter("--as required")

    valid, error = validate_domain_path(domain)
    if not valid:
        raise typer.BadParameter(f"Invalid domain: {error}")

    agent = spawn.get_agent(contributor)
    agent_id = agent.agent_id if agent else None
    if not agent_id:
        output.out_text(f"Agent not found: {contributor}", ctx.obj)
        return
    knowledge_id = api.add_knowledge(domain, agent_id, content)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"knowledge_id": knowledge_id}))
    else:
        output.out_text(f"Added to {domain}: {knowledge_id[-8:]} by {contributor}", ctx.obj)


@app.command("tree")
@error_feedback
def tree(
    ctx: typer.Context,
    domain: str = typer.Argument(None, help="Domain path to show subtree (optional)"),
    show_all: bool = typer.Option(False, "--all", help="Include archived"),
):
    """Show domain hierarchy as tree.

    Examples:
      knowledge tree                      # Show all domains
      knowledge tree architecture         # Show architecture subtree
    """
    tree_data = api.get_domain_tree(domain, show_all)

    def print_tree(node: dict, prefix: str = "", is_last: bool = True):
        items = [(k, v) for k, v in node.items() if k != "__ids"]
        for i, (key, value) in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "

            if isinstance(value, dict) and "__ids" in value:
                ids_str = " ".join(f"[{id}]" for id in value["__ids"])
                output.out_text(f"{prefix}{current_prefix}{key} {ids_str}", ctx.obj)
                subtree = {k: v for k, v in value.items() if k != "__ids"}
                if subtree:
                    next_prefix = prefix + ("    " if is_last_item else "│   ")
                    print_tree(subtree, next_prefix, is_last_item)
            else:
                output.out_text(f"{prefix}{current_prefix}{key}", ctx.obj)
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                if isinstance(value, dict) and value:
                    print_tree(value, next_prefix, is_last_item)

    if not tree_data:
        output.out_text("No domains found.", ctx.obj)
        return

    output.out_text("Domain hierarchy:", ctx.obj)
    print_tree(tree_data)


@app.command("list")
def list_knowledge(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """List all knowledge entries (metadata only)."""
    entries = api.list_knowledge(show_all=show_all)
    if not entries:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text("No knowledge entries found.", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
        return

    output.out_text("Knowledge entries:", ctx.obj)
    for e in entries:
        mark = " [ARCHIVED]" if e.archived_at else ""
        agent = spawn.get_agent(e.agent_id)
        contributor = agent.identity if agent else e.agent_id[:8]
        output.out_text(
            f"[{e.knowledge_id[-8:]}] {e.domain} ({contributor}){mark}",
            ctx.obj,
        )


@app.command("query")
def query_domain(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to query"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """Find entries for specific domain.

    Examples:
      knowledge query architecture/caching           # Exact match
      knowledge query architecture/caching --all     # Include archived
    """
    entries = api.query_knowledge(domain, show_all=show_all)
    if not entries:
        output.out_text(f"No entries for domain '{domain}'", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
        return

    output.out_text(f"Domain: {domain} ({len(entries)} entries)", ctx.obj)
    for e in entries:
        mark = " [ARCHIVED]" if e.archived_at else ""
        agent = spawn.get_agent(e.agent_id)
        contributor = agent.identity if agent else e.agent_id[:8]
        output.out_text(f"[{e.knowledge_id[-8:]}] {e.content} ({contributor}){mark}", ctx.obj)


@app.command("read")
def read(
    ctx: typer.Context,
    knowledge_id: str = typer.Argument(..., help="Knowledge ID to read"),
):
    """Read full entry details."""
    from space.lib.uuid7 import resolve_id

    try:
        full_id = resolve_id(
            "knowledge", "knowledge_id", knowledge_id, error_context="knowledge read"
        )
    except ValueError as e:
        output.out_text(f"Error: {e}", ctx.obj)
        return

    entry = api.get_knowledge(full_id)
    if not entry:
        output.out_text(f"Not found: {knowledge_id}", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json(asdict(entry)))
        return

    agent = spawn.get_agent(entry.agent_id)
    contributor = agent.identity if agent else entry.agent_id
    output.out_text(f"ID: {entry.knowledge_id}", ctx.obj)
    output.out_text(f"Domain: {entry.domain}", ctx.obj)
    output.out_text(f"Contributor: {contributor}", ctx.obj)
    output.out_text(f"Created: {entry.created_at}", ctx.obj)
    if entry.archived_at:
        output.out_text(f"Archived: {entry.archived_at}", ctx.obj)
    output.out_text(f"\n{entry.content}", ctx.obj)


@app.command("archive")
@error_feedback
def archive(
    ctx: typer.Context,
    knowledge_id: str = typer.Argument(..., help="Knowledge ID to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore knowledge."""
    from space.lib.uuid7 import resolve_id

    try:
        full_id = resolve_id(
            "knowledge", "knowledge_id", knowledge_id, error_context="knowledge archive"
        )
    except ValueError as e:
        output.out_text(f"Error: {e}", ctx.obj)
        return

    entry = api.get_knowledge(full_id)
    if not entry:
        output.out_text(f"Not found: {knowledge_id}", ctx.obj)
        return

    try:
        api.archive_knowledge(full_id, restore=restore)
        action = "restored" if restore else "archived"
        output.out_text(f"{action} {knowledge_id[-8:]}", ctx.obj)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def main() -> None:
    """Entry point for knowledge command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        typer.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


__all__ = ["app", "main"]
