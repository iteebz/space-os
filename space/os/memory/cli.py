"""Memory CLI: Knowledge Base Management."""

from dataclasses import asdict
from typing import Annotated

import typer

from space.lib import display, errors, output
from space.lib.format import format_memory_entries
from space.os import spawn
from space.os.memory import api

errors.install_error_handler("memory")


main_app = typer.Typer(
    invoke_without_command=True,
    add_completion=False,
    help="""Your continuity is yours to manage. Store observations, tasks, beliefs.
Archive when done. Mark core memories that define you. No permission needed—just write.""",
)


@main_app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    identity: Annotated[str | None, typer.Option("--as", help="Agent identity to use.")] = None,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format.")
    ] = False,
    quiet_output: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress non-essential output.")
    ] = False,
):
    output.set_flags(ctx, json_output, quiet_output)

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj["identity"] = identity
    ctx.obj["json"] = json_output
    ctx.obj["quiet"] = quiet_output

    if ctx.resilient_parsing:
        return

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@main_app.command("tree")
def tree(
    ctx: typer.Context,
    topic: str = typer.Argument(None, help="Topic path to show subtree (optional)"),
    show_all: bool = typer.Option(False, "--all", help="Include archived"),
):
    """Show topic hierarchy as tree.

    Examples:
      memory tree --as sentinel                      # Show all topics for agent
      memory tree --as sentinel --topic observations # Show observations subtree
    """
    ident = ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(ident)
    if not agent:
        raise typer.BadParameter(f"Identity '{ident}' not registered.")
    agent_id = agent.agent_id

    tree_data = api.get_topic_tree(agent_id, topic, show_all)

    def print_tree(node: dict, prefix: str = "", is_last: bool = True):
        items = list(node.items())
        for i, (key, subtree) in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "
            output.out_text(f"{prefix}{current_prefix}{key}", ctx.obj)
            next_prefix = prefix + ("    " if is_last_item else "│   ")
            if subtree:
                print_tree(subtree, next_prefix, is_last_item)

    if not tree_data:
        output.out_text("No topics found.", ctx.obj)
        return

    output.out_text("Topic hierarchy:", ctx.obj)
    print_tree(tree_data)


@main_app.command("add")
def add(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic path (e.g., observations/tasks/priority)"),
    message: str = typer.Argument(..., help="The memory message"),
):
    """Create new memory entry.

    Example:
      memory add observations/tasks/urgent "Fix bug in caching layer" --as sentinel
    """
    from space.lib.paths import validate_domain_path

    valid, error = validate_domain_path(topic)
    if not valid:
        raise typer.BadParameter(f"Invalid topic: {error}")

    ident = ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(ident)
    if not agent:
        raise typer.BadParameter(f"Identity '{ident}' not registered.")
    agent_id = agent.agent_id
    entry_id = api.add_entry(agent_id, topic, message)
    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"entry_id": entry_id}))
    else:
        output.out_text(f"Added to {topic}: {entry_id[-8:]}", ctx.obj)


@main_app.command("edit")
def edit(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to edit"),
    message: str = typer.Argument(..., help="The new message content"),
):
    """Update memory content by UUID."""
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        api.edit_entry(uuid, message)
        output.out_text(f"Edited {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "edit", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("list")
def list(
    ctx: typer.Context,
    ident: str = typer.Option(None, "--identity"),
    topic: str = typer.Option(None, help="Topic name"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """List all memories for agent (--topic to filter)."""
    identity = ident or ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")
    try:
        entries = api.list_entries(identity, topic, show_all=show_all)
    except ValueError as e:
        output.emit_error("memory", None, "list", e)
        raise typer.BadParameter(str(e)) from e

    entries.sort(key=lambda e: (not e.core, e.timestamp), reverse=True)
    if not entries:
        output.out_text("No entries", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
    else:
        output.out_text(format_memory_entries(entries, raw_output=raw_output), ctx.obj)
        if not ctx.obj.get("quiet_output"):
            display.show_context(identity)


@main_app.command("query")
def query(
    ctx: typer.Context,
    topic: str = typer.Argument(..., help="Topic path to query"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """Query memories by topic path.

    Examples:
      memory query observations/tasks --as sentinel          # Exact match
      memory query observations/tasks --as sentinel --all    # Include archived
    """
    ident = ctx.obj.get("identity")
    if not ident:
        raise typer.BadParameter("--as required")
    try:
        entries = api.list_entries(ident, topic, show_all=show_all)
    except ValueError as e:
        output.emit_error("memory", None, "query", e)
        raise typer.BadParameter(str(e)) from e

    entries.sort(key=lambda e: (not e.core, e.timestamp), reverse=True)
    if not entries:
        output.out_text(f"No entries for topic '{topic}'", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(e) for e in entries]))
    else:
        output.out_text(f"Topic: {topic} ({len(entries)} entries)", ctx.obj)
        output.out_text(format_memory_entries(entries, raw_output=raw_output), ctx.obj)


@main_app.command("archive")
def archive(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived entry"),
):
    """Archive or restore memory."""
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        api.archive_entry(uuid, restore=restore)
        action = "restored" if restore else "archived"
        output.out_text(f"{action} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "archive", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("core")
def core(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to toggle as core"),
):
    """Toggle core memory status (★)."""
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        is_core = api.toggle_core(uuid)
        output.out_text(f"{'★' if is_core else ''} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("memory", entry.agent_id, "core", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("inspect")
def inspect(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the entry to inspect"),
    limit: int = typer.Option(5, help="Number of related entries to show"),
    show_all: bool = typer.Option(False, "--all", help="Show all entries"),
):
    """View memory and find related entries."""
    identity_name = ctx.obj.get("identity")
    if not identity_name:
        raise typer.BadParameter("--as required")
    agent = spawn.get_agent(identity_name)
    if not agent:
        raise typer.BadParameter(f"Identity '{identity_name}' not registered.")
    agent_id = agent.agent_id
    try:
        entry = api.get_by_id(uuid)
    except ValueError as e:
        output.emit_error("memory", agent_id, "inspect", e)
        raise typer.BadParameter(str(e)) from e

    if not entry:
        output.out_text("Not found", ctx.obj)
        return

    if entry.agent_id != agent_id:
        agent = spawn.get_agent(entry.agent_id)
        name = agent.identity if agent else entry.agent_id
        output.out_text(f"Belongs to {name}", ctx.obj)
        return

    related = api.find_related(entry, limit=limit, show_all=show_all)
    if ctx.obj.get("json_output"):
        payload = {
            "entry": asdict(entry),
            "related": [{"entry": asdict(r[0]), "overlap": r[1]} for r in related],
        }
        typer.echo(output.out_json(payload))
    else:
        display.show_memory_entry(entry, ctx.obj, related=related)


def main() -> None:
    """Entry point for memory command."""
    try:
        main_app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


app = main_app

__all__ = ["app", "main"]
