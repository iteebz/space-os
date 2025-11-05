"""Spawn CLI: Agent Management & Task Orchestration."""

import contextlib
import json
import os
import signal
import sys
from typing import NoReturn

import typer

from space.apps.space.api.stats import agent_stats
from space.cli import output
from space.cli.errors import error_feedback
from space.core.models import TaskStatus
from space.lib import providers
from space.os.spawn import api
from space.os.spawn.api import spawns
from space.os.spawn.formatting import (
    display_agent_trace,
    display_channel_trace,
    display_session_trace,
)

app = typer.Typer(invoke_without_command=True, add_completion=False, no_args_is_help=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Constitutional identity registry. Register agents with constitution, spawn by identity, track execution."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            identity = sys.argv[1]
            agent = api.get_agent(identity)
            if agent:
                resume, extra_args = _extract_resume_flag(sys.argv[2:])
                if extra_args:
                    typer.echo(f"Spawning {identity}...\n")
                    spawn = api.spawn_ephemeral(
                        identity, " ".join(extra_args), channel_id=None, resume=resume
                    )
                    typer.echo(f"\nSpawn ID: {spawn.id[:8]}")
                    typer.echo(f"Track: spawn trace {spawn.id[:8]}")
                else:
                    api.spawn_interactive(identity, resume=resume)
                raise typer.Exit(0)
        typer.echo(ctx.get_help())


def _resolve_identity(stat_identity: str) -> str:
    """Resolve agent identity from stat record (may be UUID)."""
    name = stat_identity or ""
    if len(name) == 36 and name.count("-") == 4:
        agent = api.get_agent(name)
        if agent:
            return agent.identity
    return name


def _extract_resume_flag(args: list[str]) -> tuple[str | None, list[str]]:
    """Extract --resume/-r flag and optional value from args.

    Returns:
        (resume_value, remaining_args) where resume_value is None if --resume not present
    """
    resume = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] in ("--resume", "-r"):
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                resume = args[i + 1]
                i += 2
            else:
                resume = ""
                i += 1
        else:
            remaining.append(args[i])
            i += 1
    return resume, remaining


@app.command()
@error_feedback
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

    sorted_stats = sorted(stats, key=lambda a: a.identity or "")
    agents_data = []

    for s in sorted_stats:
        agent_id = s.agent_id
        if not agent_id:
            continue

        name = _resolve_identity(s.identity)
        agent = api.get_agent(agent_id)

        agents_data.append(
            {
                "identity": name,
                "agent_id": agent_id,
                "constitution": agent.constitution if agent and agent.constitution else "-",
                "model": agent.model if agent and agent.model else "-",
                "role": agent.role if agent and agent.role else "-",
            }
        )

    if json_output:
        typer.echo(json.dumps(agents_data))
    else:
        typer.echo(f"{'IDENTITY':<15} {'CONSTITUTION':<15} {'MODEL':<20} {'ROLE':<15}")
        for data in agents_data:
            typer.echo(
                f"{data['identity']:<15} {data['constitution']:<15} {data['model']:<20} {data['role']:<15}"
            )
        typer.echo()
        typer.echo(f"Total: {len(agents_data)}")


@app.command()
@error_feedback
def register(
    identity: str,
    model: str = typer.Option(
        ..., "--model", "-m", help="Model ID. Run 'spawn models' to list available models"
    ),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename (e.g., zealot.md) - optional"
    ),
    role: str | None = typer.Option(
        None, "--role", "-r", help="Organizational role (e.g., executor, verifier, adversary)"
    ),
):
    """Register a new agent."""
    try:
        agent_id = api.register_agent(identity, model, constitution, role)
        typer.echo(f"✓ Registered {identity} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def models():
    """Show available LLM models."""
    for prov in ["claude", "codex", "gemini"]:
        provider_models = providers.MODELS.get(prov, [])
        typer.echo(f"\n📦 {prov.capitalize()} Models:\n")
        for model in provider_models:
            typer.echo(f"  • {model['name']} ({model['id']})")
            if model.get("description"):
                typer.echo(f"    {model['description']}")
            typer.echo()


@app.command()
@error_feedback
def clone(src: str, dst: str):
    """Copy agent with new identity."""
    try:
        agent_id = api.clone_agent(src, dst)
        typer.echo(f"✓ Cloned {src} → {dst} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
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
@error_feedback
def update(
    identity: str,
    model: str | None = typer.Option(None, "--model", "-m", help="Full model name"),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename"
    ),
    role: str | None = typer.Option(None, "--role", "-r", help="Organizational role"),
):
    """Modify agent fields (constitution, model, role)."""
    try:
        api.update_agent(identity, constitution, model, role)
        typer.echo(f"✓ Updated {identity}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def inspect(identity: str):
    """View agent details and constitution."""
    from space.lib import paths

    agent = api.get_agent(identity)
    if not agent:
        typer.echo(f"❌ Agent not found: {identity}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nAgent: {agent.identity}")
    typer.echo(f"ID: {agent.agent_id}")
    typer.echo(f"Model: {agent.model}")
    typer.echo(f"Constitution: {agent.constitution or '-'}")
    typer.echo(f"Role: {agent.role or '-'}")
    typer.echo(f"Spawns: {agent.spawn_count}")
    typer.echo(f"Created: {agent.created_at}")
    typer.echo(f"Last Active: {agent.last_active_at or '-'}")

    if agent.constitution:
        const_path = paths.constitution(agent.constitution)
        if const_path.exists():
            typer.echo(f"\n--- {agent.constitution} ---")
            typer.echo(const_path.read_text())
        else:
            typer.echo(f"\n⚠️ Constitution file not found: {const_path}")
    typer.echo()


@app.command()
@error_feedback
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
    identity: str | None = None,
    all: bool = typer.Option(
        False, "--all", "-a", help="Show all spawns (including completed/failed)"
    ),
):
    """List spawns (filter by status/identity).

    Default: Show pending and running spawns only.
    With --all/-a: Show all spawns including completed/failed/timeout.
    """
    if not all and status is None:
        status = "pending|running"

    # Get agent if filtering by identity
    agent = None
    if identity:
        agent = api.get_agent(identity)
        if not agent:
            typer.echo(f"❌ Agent not found: {identity}", err=True)
            raise typer.Exit(1)

    # Get spawns
    if agent:
        all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    else:
        # For now, just get empty list if no agent specified
        # Could extend to get all spawns across agents
        typer.echo("Please specify --identity to list spawns")
        return

    # Filter by status
    if status and "|" in status:
        statuses = status.split("|")
        spawns_list = [s for s in all_spawns if s.status in statuses]
    else:
        spawns_list = [s for s in all_spawns if status is None or s.status == status]

    if not spawns_list:
        typer.echo("No spawns.")
        return

    typer.echo(f"{'ID':<8} {'Status':<12} {'Created':<20}")
    typer.echo("-" * 40)

    for spawn_obj in spawns_list:
        spawn_id = spawn_obj.id[:8]
        stat = spawn_obj.status
        created = spawn_obj.created_at[:19] if spawn_obj.created_at else "-"
        typer.echo(f"{spawn_id:<8} {stat:<12} {created:<20}")


@app.command()
@error_feedback
def logs(spawn_id: str):
    """Show spawn details."""
    spawn_obj = spawns.get_spawn(spawn_id)
    if not spawn_obj:
        typer.echo(f"❌ Spawn not found: {spawn_id}", err=True)
        raise typer.Exit(1)
    if not spawn_obj.agent_id:
        typer.echo(f"❌ Spawn has invalid agent_id: {spawn_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n📋 Spawn: {spawn_obj.id}")
    typer.echo(f"Agent: {spawn_obj.agent_id}")
    typer.echo(f"Status: {spawn_obj.status}")
    typer.echo(f"Is Ephemeral: {spawn_obj.is_ephemeral}")

    if spawn_obj.channel_id:
        typer.echo(f"Channel: {spawn_obj.channel_id}")

    if spawn_obj.session_id:
        typer.echo(f"Session: {spawn_obj.session_id}")

    typer.echo(f"Created: {spawn_obj.created_at}")
    if spawn_obj.ended_at:
        typer.echo(f"Ended: {spawn_obj.ended_at}")

    typer.echo()


@app.command()
@error_feedback
def kill(spawn_id: str):
    """Stop running spawn."""
    spawn_obj = spawns.get_spawn(spawn_id)
    if not spawn_obj:
        typer.echo(f"❌ Spawn not found: {spawn_id}", err=True)
        raise typer.Exit(1)

    if spawn_obj.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT):
        typer.echo(f"⚠️ Spawn already {spawn_obj.status}, nothing to kill")
        return

    if spawn_obj.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(spawn_obj.pid, signal.SIGTERM)

    spawns.update_status(spawn_id, TaskStatus.FAILED)
    typer.echo(f"✓ Spawn {spawn_id[:8]} killed")


@app.command()
@error_feedback
def trace(query: str = typer.Argument(None)):
    """Trace execution: agent spawns, session context, or channel activity.

    Query syntax:
    - Explicit: agent:zealot, session:7a6a07de, channel:general (recommended)
    - Implicit: zealot, 7a6a07de, general (auto-inferred)
    """
    if query is None:
        typer.echo("Usage: spawn trace [QUERY]")
        typer.echo("Query syntax:")
        typer.echo("  - Explicit: agent:zealot, session:7a6a07de, channel:general")
        typer.echo("  - Implicit: zealot, 7a6a07de, general (auto-inferred)")
        raise typer.Exit(0)

    try:
        result = api.trace_query(query)
    except ValueError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1) from e

    if result["type"] == "identity":
        display_agent_trace(result)
    elif result["type"] == "session":
        display_session_trace(result)
    elif result["type"] == "channel":
        display_channel_trace(result)


def dispatch_agent_from_name() -> NoReturn:
    """Entry point: route command name (argv[0]) to agent if registered."""
    prog_name = sys.argv[0].split("/")[-1]

    agent = api.get_agent(prog_name)
    if not agent:
        click.echo(f"Error: '{prog_name}' is not a registered agent identity.", err=True)
        click.echo("Run 'spawn agents' to list available agents.", err=True)
        sys.exit(1)

    args = sys.argv[1:] if len(sys.argv) > 1 else []
    resume, extra_args = _extract_resume_flag(args)
    if extra_args:
        api.spawn_ephemeral(agent.identity, " ".join(extra_args), channel_id=None, resume=resume)
    else:
        api.spawn_interactive(agent.identity, resume=resume)
    sys.exit(0)


def main() -> None:
    """Entry point for spawn command."""
    try:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            potential_identity = sys.argv[1]
            agent = api.get_agent(potential_identity)
            if agent:
                resume, extra_args = _extract_resume_flag(sys.argv[2:])
                if extra_args:
                    typer.echo(f"Spawning {potential_identity}...\n")
                    spawn = api.spawn_ephemeral(
                        potential_identity, " ".join(extra_args), channel_id=None, resume=resume
                    )
                    typer.echo(f"\nSpawn ID: {spawn.id[:8]}")
                    typer.echo(f"Track: spawn trace {spawn.id[:8]}")
                else:
                    api.spawn_interactive(potential_identity, resume=resume)
                return
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main", "dispatch_agent_from_name"]
