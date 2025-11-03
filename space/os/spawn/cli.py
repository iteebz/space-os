"""Spawn CLI: Agent Management & Task Orchestration."""

import contextlib
import json
import os
import signal
import sys
from typing import NoReturn

import typer

from space.apps.space.api.stats import agent_stats
from space.core.models import TaskStatus
from space.lib import errors, output
from space.os.spawn import api
from space.os.spawn import models as models_module
from space.os.spawn.api import tasks

errors.install_error_handler("spawn")


app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Register and manage agents. Track tasks and execution."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def agents(
    show_all: bool = typer.Option(False, "--all", help="Show archived agents"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List registered and orphaned agents."""
    stats = agent_stats(show_all=show_all) or []

    if not stats:
        if json_output:
            typer.echo(json.dumps([]))
        else:
            typer.echo("No agents found.")
        return

    if json_output:
        agents_data = []
        for s in sorted(stats, key=lambda a: a.identity or ""):
            agent_id = s.agent_id
            if not agent_id:
                continue
            name = s.identity or ""
            if len(name) == 36 and name.count("-") == 4:
                agent = api.get_agent(name)
                if agent:
                    name = agent.identity
            agent = api.get_agent(agent_id)
            agents_data.append(
                {
                    "identity": name,
                    "agent_id": agent_id,
                    "model": agent.model if agent and agent.model else "-",
                    "description": agent.description if agent and agent.description else "-",
                }
            )
        typer.echo(json.dumps(agents_data))
    else:
        typer.echo(f"{'IDENTITY':<20} {'AGENT_ID':<10} {'MODEL':<25} {'DESCRIPTION'}")

        for s in sorted(stats, key=lambda a: a.identity or ""):
            name = s.identity or ""
            agent_id = s.agent_id
            if not agent_id:
                continue
            short_id = agent_id[:8]

            if len(name) == 36 and name.count("-") == 4:
                agent = api.get_agent(name)
                if agent:
                    name = agent.identity

            agent = api.get_agent(agent_id)
            model = agent.model if agent and agent.model else "-"
            desc = agent.description if agent and agent.description else "-"

            typer.echo(f"{name:<20} {short_id:<10} {model:<25} {desc}")

        typer.echo()
        typer.echo(f"Total: {len(stats)}")


@app.command()
def register(
    identity: str,
    model: str = typer.Option(
        ..., "--model", "-m", help="Model ID. Run 'spawn models' to list available models"
    ),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename (e.g., zealot.md) - optional"
    ),
):
    """Register a new agent."""
    try:
        agent_id = api.register_agent(identity, model, constitution)
        typer.echo(f"✓ Registered {identity} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def models():
    """Show available LLM models."""
    for prov in ["claude", "codex", "gemini"]:
        provider_models = models_module.get_models_for_provider(prov)
        typer.echo(f"\n📦 {prov.capitalize()} Models:\n")
        for model in provider_models:
            typer.echo(f"  • {model.name} ({model.id})")
            if model.description:
                typer.echo(f"    {model.description}")
            if model.reasoning_levels:
                typer.echo(f"    Reasoning levels: {', '.join(model.reasoning_levels)}")
            typer.echo()


@app.command()
def clone(src: str, dst: str):
    """Copy agent with new identity."""
    try:
        agent_id = api.clone_agent(src, dst)
        typer.echo(f"✓ Cloned {src} → {dst} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def rename(old_name: str, new_name: str):
    """Change agent identity."""
    try:
        if api.rename_agent(old_name, new_name):
            typer.echo(f"✓ Renamed {old_name} → {new_name}")
        else:
            typer.echo(f"❌ Agent not found: {old_name}. Run `spawn` to list agents.", err=True)
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def update(
    identity: str,
    model: str = typer.Option(None, "--model", "-m", help="Full model name"),
    constitution: str = typer.Option(None, "--constitution", "-c", help="Constitution filename"),
):
    """Modify agent fields (description, model)."""
    try:
        api.update_agent(identity, constitution, model)
        typer.echo(f"✓ Updated {identity}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def merge(id_from: str, id_to: str):
    """Consolidate data from one agent to another."""
    agent_from = api.get_agent(id_from)
    agent_to = api.get_agent(id_to)

    if not agent_from:
        typer.echo(f"Error: Agent '{id_from}' not found")
        raise typer.Exit(1)
    if not agent_to:
        typer.echo(f"Error: Agent '{id_to}' not found")
        raise typer.Exit(1)

    result = api.merge_agents(id_from, id_to)

    if not result:
        typer.echo("Error: Could not merge agents")
        raise typer.Exit(1)

    from_display = agent_from.identity or id_from[:8]
    to_display = agent_to.identity or id_to[:8]
    typer.echo(f"Merging {from_display} → {to_display}")
    typer.echo("✓ Merged")


@app.command(name="tasks")
def show_tasks(
    status: str | None = None,
    role: str | None = None,
    all: bool = typer.Option(
        False, "--all", "-a", help="Show all tasks (including completed/failed)"
    ),
):
    """List tasks (filter by status/role).

    Default: Show pending and running tasks only.
    With --all/-a: Show all tasks including completed/failed/timeout.
    """
    if not all and status is None:
        status = "pending|running"

    if status and "|" in status:
        statuses = status.split("|")
        all_tasks = tasks.list_tasks(status=None, role=role)
        tasks_list = [t for t in all_tasks if t.status in statuses]
    else:
        tasks_list = tasks.list_tasks(status=status, role=role)

    if not tasks_list:
        typer.echo("No tasks.")
        return

    typer.echo(f"{'ID':<8} {'Identity':<12} {'Status':<12} {'Duration':<10} {'Created':<20}")
    typer.echo("-" * 70)

    durations = []
    for task in tasks_list:
        task_id = task.task_id[:8]
        ident = (task.agent_id or "unknown")[:11]
        stat = task.status
        dur = f"{task.duration:.1f}s" if task.duration else "-"
        created = task.created_at[:19] if task.created_at else "-"
        typer.echo(f"{task_id:<8} {ident:<12} {stat:<12} {dur:<10} {created:<20}")
        if task.duration:
            durations.append(task.duration)

    if durations:
        typer.echo("-" * 70)
        avg_dur = sum(durations) / len(durations)
        min_dur = min(durations)
        max_dur = max(durations)
        typer.echo(f"Avg: {avg_dur:.1f}s | Min: {min_dur:.1f}s | Max: {max_dur:.1f}s")


@app.command()
def logs(task_id: str):
    """Show full task details (input, output, stderr)."""
    task = tasks.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)
    if not task.agent_id:
        typer.echo(f"❌ Task has invalid agent_id: {task_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n📋 Task: {task.task_id}")
    typer.echo(f"Identity: {task.agent_id}")
    typer.echo(f"Status: {task.status}")

    if task.channel_id:
        typer.echo(f"Channel: {task.channel_id}")

    typer.echo(f"Created: {task.created_at}")
    if task.started_at:
        typer.echo(f"Started: {task.started_at}")
    if task.completed_at:
        typer.echo(f"Completed: {task.completed_at}")
    if task.duration is not None:
        typer.echo(f"Duration: {task.duration:.2f}s")

    typer.echo("\n--- Input ---")
    typer.echo(task.input)

    if task.output:
        typer.echo("\n--- Output ---")
        typer.echo(task.output)

    if task.stderr:
        typer.echo("\n--- Stderr ---")
        typer.echo(task.stderr)

    typer.echo()


@app.command()
def kill(task_id: str):
    """Stop running task."""
    task = tasks.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT):
        typer.echo(f"⚠️ Task already {task.status}, nothing to kill")
        return

    if task.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(task.pid, signal.SIGTERM)

    tasks.fail_task(task_id, stderr="Killed by user")
    typer.echo(f"✓ Task {task_id[:8]} killed")


def dispatch_agent_from_name() -> NoReturn:
    """Entry point: route command name (argv[0]) to agent if registered."""
    prog_name = sys.argv[0].split("/")[-1]

    agent = api.get_agent(prog_name)
    if not agent:
        click.echo(f"Error: '{prog_name}' is not a registered agent identity.", err=True)
        click.echo("Run 'spawn agents' to list available agents.", err=True)
        sys.exit(1)

    args = sys.argv[1:] if len(sys.argv) > 1 else []
    api.spawn_agent(agent.identity, extra_args=args)
    sys.exit(0)


def main() -> None:
    """Entry point for spawn command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main", "dispatch_agent_from_name"]
