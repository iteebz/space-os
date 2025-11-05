"""Task CLI: shared work ledger."""

from typing import Annotated

import typer

from space.cli import argv, output
from space.cli.errors import error_feedback
from space.os import spawn
from space.os.task import api
from space.os.task.format import format_task_list

argv.flex_args("as")

main_app = typer.Typer(
    invoke_without_command=True,
    add_completion=False,
    help="""Shared work ledger. Prevents duplication at scale. Agents claim work, humans orchestrate.""",
)


@main_app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    identity: Annotated[str | None, typer.Option("--as", help="Agent identity.")] = None,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["identity"] = identity

    if ctx.resilient_parsing:
        return

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@main_app.command("add")
@error_feedback
def add(
    ctx: typer.Context,
    content: str = typer.Argument(..., help="Task description"),
    project: Annotated[str | None, typer.Option("--project", help="Project/epic name")] = None,
):
    """Create new task."""
    identity = ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")

    agent = spawn.get_agent(identity)
    if not agent:
        raise typer.BadParameter(f"Identity '{identity}' not registered")

    task_id = api.add_task(content, creator_id=agent.agent_id, project=project)
    output.out_text(f"Added: {task_id[-8:]}", ctx.obj)


@main_app.command("list")
@error_feedback
def list_cmd(
    ctx: typer.Context,
    project: Annotated[str | None, typer.Option("--project", help="Filter by project")] = None,
    by_agent: Annotated[str | None, typer.Option("--as", help="Filter by claimed agent")] = None,
    show_done: bool = typer.Option(False, "--done", help="Show completed tasks"),
    show_all: bool = typer.Option(False, "--all", help="Show all (open + in_progress + done)"),
):
    """List tasks."""
    status = None
    if show_done:
        status = "done"
    elif show_all:
        status = None  # Will show all via list_tasks logic

    if show_all:
        # Override: fetch all statuses
        tasks = api.list_tasks(status=None, project=project, agent_id=None)
        # Filter by agent if specified
        if by_agent:
            agent = spawn.get_agent(by_agent)
            if not agent:
                raise typer.BadParameter(f"Identity '{by_agent}' not registered")
            tasks = [t for t in tasks if t.agent_id == agent.agent_id]
    else:
        # Fetch status-filtered tasks
        agent_id = None
        if by_agent:
            agent = spawn.get_agent(by_agent)
            if not agent:
                raise typer.BadParameter(f"Identity '{by_agent}' not registered")
            agent_id = agent.agent_id

        tasks = api.list_tasks(status=status, project=project, agent_id=agent_id)

    if not tasks:
        output.out_text("No tasks", ctx.obj)
        return

    output.out_text(format_task_list(tasks), ctx.obj)


@main_app.command("start")
@error_feedback
def start(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to claim"),
    remove: bool = typer.Option(False, "-r", "--remove", help="Unclaim task"),
):
    """Claim task or unclaim if -r."""
    identity = ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")

    agent = spawn.get_agent(identity)
    if not agent:
        raise typer.BadParameter(f"Identity '{identity}' not registered")

    try:
        if remove:
            api.remove_claim(task_id, agent.agent_id)
            output.out_text(f"Unclaimed: {task_id[-8:]}", ctx.obj)
        else:
            api.start_task(task_id, agent.agent_id)
            output.out_text(f"Claimed: {task_id[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("task", agent.agent_id, "start", e)
        raise typer.BadParameter(str(e)) from e


@main_app.command("done")
@error_feedback
def done(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to complete"),
):
    """Mark task as complete."""
    identity = ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("--as required")

    agent = spawn.get_agent(identity)
    if not agent:
        raise typer.BadParameter(f"Identity '{identity}' not registered")

    try:
        api.done_task(task_id, agent.agent_id)
        output.out_text(f"Completed: {task_id[-8:]}", ctx.obj)
    except ValueError as e:
        output.emit_error("task", agent.agent_id, "done", e)
        raise typer.BadParameter(str(e)) from e


def main() -> None:
    """Entry point for task command."""
    try:
        main_app()
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from e


app = main_app

__all__ = ["app", "main"]
