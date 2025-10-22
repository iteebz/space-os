"""Ops CLI - work decomposition and coordination for agent swarms."""

from dataclasses import asdict

import typer

from space.lib import errors, output, readme
from space.spawn import registry

from . import api

errors.install_error_handler("ops")

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main_command(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
    help: bool = typer.Option(False, "--help", "-h", help="Show help"),
):
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if help:
        typer.echo(readme.load("ops"))
        ctx.exit()

    if ctx.resilient_parsing or ctx.invoked_subcommand is None:
        typer.echo(readme.load("ops"))
    return


@app.command("create")
def create_task_command(
    ctx: typer.Context,
    description: str = typer.Argument(..., help="Task description"),
    parent: str = typer.Option(None, "--parent", help="Parent task ID"),
    channel: str = typer.Option(None, "--channel", help="Bridge channel for coordination"),
    assign: str = typer.Option(None, "--assign", help="Agent identity to assign"),
):
    """Create a new task."""
    assigned_to = None
    if assign:
        assigned_to = registry.ensure_agent(assign)

    task_id = api.create(description, parent, channel, assigned_to)

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"task_id": task_id}))
    else:
        output.out_text(f"Created task {task_id[-8:]}", ctx.obj)
        if parent:
            output.out_text(f"  Parent: {parent[-8:]}", ctx.obj)
        if assign:
            output.out_text(f"  Assigned to: {assign}", ctx.obj)


@app.command("list")
def list_tasks_command(
    ctx: typer.Context,
    status: str = typer.Option(None, help="Filter by status (open, claimed, complete, blocked)"),
    assigned: str = typer.Option(None, "--assigned", help="Filter by assigned agent identity"),
    parent: str = typer.Option(None, "--parent", help="Filter by parent task ID (empty for roots)"),
):
    """List tasks with optional filters."""
    assigned_to = None
    if assigned:
        assigned_to = registry.get_agent_id(assigned)
        if not assigned_to:
            output.out_text(f"Agent '{assigned}' not found", ctx.obj)
            return

    tasks = api.list_tasks(status=status, assigned_to=assigned_to, parent_id=parent or None)

    if not tasks:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json([]))
        else:
            output.out_text("No tasks found", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json([asdict(task) for task in tasks]))
    else:
        for task in tasks:
            assigned_name = ""
            if task.assigned_to:
                identity = registry.get_identity(task.assigned_to)
                assigned_name = f" @{identity}" if identity else ""

            output.out_text(
                f"[{task.task_id[-8:]}] {task.status.upper()}{assigned_name} - {task.description}",
                ctx.obj,
            )
            if task.parent_id:
                output.out_text(f"  Parent: {task.parent_id[-8:]}", ctx.obj)


@app.command("tree")
def tree_command(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to show tree for"),
):
    """Show task decomposition tree."""
    tree_data = api.tree(task_id)

    if not tree_data:
        if ctx.obj.get("json_output"):
            typer.echo(output.out_json(None))
        else:
            output.out_text(f"Task {task_id} not found", ctx.obj)
        return

    if ctx.obj.get("json_output"):

        def serialize_tree(node):
            return {
                "task": asdict(node["task"]),
                "subtasks": [serialize_tree(st) for st in node["subtasks"]],
            }

        typer.echo(output.out_json(serialize_tree(tree_data)))
    else:

        def print_tree(node, prefix="", is_last=True):
            task = node["task"]
            connector = "└── " if is_last else "├── "
            assigned_name = ""
            if task.assigned_to:
                identity = registry.get_identity(task.assigned_to)
                assigned_name = f" @{identity}" if identity else ""

            output.out_text(
                f"{prefix}{connector}[{task.task_id[-8:]}] {task.status.upper()}{assigned_name} - {task.description}",
                ctx.obj,
            )

            subtasks = node["subtasks"]
            for i, subtask in enumerate(subtasks):
                extension = "    " if is_last else "│   "
                print_tree(subtask, prefix + extension, i == len(subtasks) - 1)

        print_tree(tree_data)


@app.command("claim")
def claim_task_command(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to claim"),
    identity: str = typer.Option(..., "--as", help="Agent identity claiming task"),
):
    """Claim a task for an agent."""
    agent_id = registry.ensure_agent(identity)
    success = api.claim(task_id, agent_id)

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"task_id": task_id, "claimed": success}))
    else:
        if success:
            output.out_text(f"Task {task_id[-8:]} claimed by {identity}", ctx.obj)
        else:
            output.out_text(f"Failed to claim task {task_id[-8:]} (already claimed or not found)", ctx.obj)


@app.command("complete")
def complete_task_command(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to complete"),
    handover: str = typer.Argument(..., help="Handover documentation"),
    identity: str = typer.Option(..., "--as", help="Agent identity completing task"),
):
    """Complete a task with handover documentation."""
    agent_id = registry.ensure_agent(identity)
    success = api.complete(task_id, handover, agent_id)

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"task_id": task_id, "completed": success}))
    else:
        if success:
            output.out_text(f"Task {task_id[-8:]} completed by {identity}", ctx.obj)
        else:
            output.out_text(
                f"Failed to complete task {task_id[-8:]} (not assigned to you or not found)", ctx.obj
            )


@app.command("block")
def block_task_command(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to block"),
    reason: str = typer.Argument(..., help="Reason for blocking"),
):
    """Block a task with a reason."""
    success = api.block(task_id, reason)

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"task_id": task_id, "blocked": success}))
    else:
        if success:
            output.out_text(f"Task {task_id[-8:]} blocked", ctx.obj)
        else:
            output.out_text(f"Failed to block task {task_id[-8:]}", ctx.obj)


@app.command("reduce")
def reduce_task_command(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Parent task ID to reduce"),
    handover: str = typer.Argument(..., help="Integration handover"),
    identity: str = typer.Option(..., "--as", help="Agent identity performing reduction"),
):
    """Reduce completed subtasks into parent task completion."""
    agent_id = registry.ensure_agent(identity)
    success = api.reduce(task_id, handover, agent_id)

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"task_id": task_id, "reduced": success}))
    else:
        if success:
            output.out_text(f"Task {task_id[-8:]} reduced by {identity}", ctx.obj)
        else:
            output.out_text(
                f"Failed to reduce task {task_id[-8:]} (incomplete subtasks or not found)", ctx.obj
            )


def main() -> None:
    """Entry point for poetry script."""
    app()
