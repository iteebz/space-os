"""Memory CLI: agent working memory management."""

from dataclasses import asdict
from typing import Annotated

import typer

from space.cli import argv, output
from space.cli.errors import error_feedback
from space.os import memory
from space.os.context import display
from space.os.memory.format import format_memory_entries

argv.flex_args("as")

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
    output.init_context(ctx, json_output, quiet_output, identity)

    if ctx.resilient_parsing:
        return

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@main_app.command("add")
@error_feedback
def add(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="The memory message"),
    topic: Annotated[str | None, typer.Option("--topic", help="Optional topic label")] = None,
):
    """Create new memory entry.

    Example:
      memory add "Fix bug in caching layer" --topic observations --as sentinel
    """
    from space.cli.identity import resolve_agent

    agent = resolve_agent(ctx)
    memory_id = memory.add_memory(agent.agent_id, message, topic=topic)
    topic_str = f" [{topic}]" if topic else ""
    output.respond(ctx, {"memory_id": memory_id}, f"Added{topic_str}: {memory_id[-8:]}")


@main_app.command("edit")
@error_feedback
def edit(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the memory to edit"),
    message: str = typer.Argument(..., help="The new message content"),
):
    """Update memory content by UUID."""
    entry = memory.get_memory(uuid)
    if not entry:
        raise typer.BadParameter(f"Memory not found: {uuid}")

    memory.edit_memory(uuid, message)
    output.echo_text(f"Edited {uuid[-8:]}", ctx)


@main_app.command("list")
@error_feedback
def list_cmd(
    ctx: typer.Context,
    topic: Annotated[str | None, typer.Option("--topic", help="Filter by topic label")] = None,
    show_all: bool = typer.Option(False, "--all", help="Show archived entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """List memories for agent (--topic to filter)."""
    from space.cli.identity import resolve_agent

    agent = resolve_agent(ctx)
    entries = memory.list_memories(agent.identity, topic=topic, show_all=show_all)
    entries = sorted(entries, key=lambda e: (not e.core, e.created_at), reverse=True)

    if not entries:
        output.echo_text("No memories", ctx)
        return

    if output.is_json_mode(ctx):
        output.echo_json([asdict(e) for e in entries], ctx)
    else:
        output.echo_text(format_memory_entries(entries, raw_output=raw_output), ctx)
        if not output.is_quiet_mode(ctx):
            display.show_context(agent.identity)


@main_app.command("search")
@error_feedback
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    show_all: bool = typer.Option(False, "--all", help="Search archived entries"),
    raw_output: bool = typer.Option(
        False, "--raw", help="Output raw timestamps instead of humanized."
    ),
):
    """Search memories by message content.

    Example:
      memory search "caching" --as sentinel
    """
    from space.cli.identity import resolve_agent

    agent = resolve_agent(ctx)
    entries = memory.list_memories(agent.identity, show_all=show_all)
    results = [e for e in entries if query.lower() in e.message.lower()]

    if not results:
        output.echo_text(f"No results for '{query}'", ctx)
        return

    if output.is_json_mode(ctx):
        output.echo_json([asdict(e) for e in results], ctx)
    else:
        output.echo_text(f"Found {len(results)} matches:", ctx)
        output.echo_text(format_memory_entries(results, raw_output=raw_output), ctx)


@main_app.command("archive")
@error_feedback
def archive(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the memory to archive"),
    restore: bool = typer.Option(False, "--restore", help="Restore archived memory"),
):
    """Archive or restore memory."""
    entry = memory.get_memory(uuid)
    if not entry:
        raise typer.BadParameter(f"Memory not found: {uuid}")

    memory.archive_memory(uuid, restore=restore)
    action = "restored" if restore else "archived"
    output.echo_text(f"{action} {uuid[-8:]}", ctx)


@main_app.command("core")
@error_feedback
def core(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the memory to mark core"),
):
    """Toggle core memory status (essential to agent identity)."""
    entry = memory.get_memory(uuid)
    if not entry:
        raise typer.BadParameter(f"Memory not found: {uuid}")
    try:
        is_core = memory.toggle_memory_core(uuid)
        output.out_text(f"{'★' if is_core else ''} {uuid[-8:]}", ctx.obj)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


@main_app.command("info")
@error_feedback
def info(
    ctx: typer.Context,
    uuid: str = typer.Argument(..., help="UUID of the memory to view"),
    limit: int = typer.Option(5, help="Number of related memories to show"),
    show_all: bool = typer.Option(False, "--all", help="Include archived"),
):
    """View memory and find related entries."""
    try:
        entry = memory.get_memory(uuid)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e

    if not entry:
        output.out_text("Not found", ctx.obj)
        return

    related = memory.find_related_memories(entry, limit=limit, show_all=show_all)
    if output.is_json_mode(ctx):
        payload = {
            "memory": asdict(entry),
            "related": [{"memory": asdict(r[0]), "overlap": r[1]} for r in related],
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
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


app = main_app

__all__ = ["app", "main"]
