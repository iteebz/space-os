"""Agent commands: list, describe, inspect, merge, delete, rename."""

import json

import typer

from space.apps import stats as stats_lib
from space.os.lib import errors

from .. import api

errors.install_error_handler("spawn")

app = typer.Typer()


@app.command("agents")
def list_agents(show_all: bool = typer.Option(False, "--all", help="Show archived agents")):
    """List all agents (registered and orphaned across universe)."""
    stats = stats_lib.agent_stats(include_archived=show_all) or []

    if not stats:
        typer.echo("No agents found.")
        return

    with api.connect() as conn:
        {row["agent_id"]: row["name"] for row in conn.execute("SELECT agent_id, name FROM agents")}

    typer.echo(f"{'NAME':<20} {'ID':<10} {'E-S-B-M-K':<20} {'SELF'}")
    typer.echo("-" * 100)

    for s in sorted(stats, key=lambda a: a.agent_name):
        name = s.agent_name
        agent_id = s.agent_id
        short_id = agent_id[:8]

        if len(name) == 36 and name.count("-") == 4:
            resolved = api.get_agent_name(name)
            if resolved:
                name = resolved

        desc = "-"
        esbmk = f"{s.events}-{s.spawns}-{s.msgs}-{s.mems}-{s.knowledge}"

        typer.echo(f"{name:<20} {short_id:<10} {esbmk:<20} {desc}")

    typer.echo()
    typer.echo(f"Total: {len(stats)}")


@app.command("describe")
def describe(
    identity: str = typer.Option(..., "--as", help="Identity to describe"),
    description: str = typer.Argument(None, help="Description to set"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """Get or set self-description for an identity."""
    if description:
        updated = api.set_self_description(identity, description)
        if json_output:
            typer.echo(
                json.dumps({"identity": identity, "description": description, "updated": updated})
            )
        elif updated:
            typer.echo(f"{identity}: {description}")
        else:
            typer.echo(f"No agent: {identity}")
    else:
        desc = api.get_self_description(identity)
        if json_output:
            typer.echo(json.dumps({"identity": identity, "description": desc}))
        elif desc:
            typer.echo(desc)
        else:
            typer.echo(f"No self-description for {identity}")


@app.command("inspect")
def inspect(agent_ref: str):
    """Inspect agent activity and state."""
    import time

    from space.os import events as events_lib

    result = _resolve_agent_id(agent_ref)

    if not result:
        typer.echo(f"Error: Agent not found for '{agent_ref}'")
        raise typer.Exit(1)

    agent_id, display_name = result
    short_id = agent_id[:8]

    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"Agent: {display_name} ({short_id})")
    typer.echo(f"{'─' * 60}\n")

    evts = events_lib.query(agent_id=agent_id, limit=50)

    if not evts:
        typer.echo("No activity recorded.")
        typer.echo()
        return

    event_types = {}
    for e in evts:
        et = e.event_type
        if et not in event_types:
            event_types[et] = 0
        event_types[et] += 1

    typer.echo("Activity summary:")
    for et, count in sorted(event_types.items(), key=lambda x: -x[1]):
        typer.echo(f"  {et}: {count}")
    typer.echo()

    typer.echo("Recent activity (last 10):")
    for e in reversed(evts[:10]):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.timestamp))
        data_str = f" ({e.data[:50]})" if e.data else ""
        typer.echo(f"  [{ts}] {e.event_type}{data_str}")

    typer.echo(f"\n{'─' * 60}\n")


@app.command("merge")
def merge(id_from: str, id_to: str):
    """Merge all data from one agent ID to another."""
    result = api.merge_agents(id_from, id_to)

    if not result:
        typer.echo("Error: Could not merge agents")
        raise typer.Exit(1)

    from_display = api.get_agent_name(id_from) or id_from[:8]
    to_display = api.get_agent_name(id_to) or id_to[:8]
    typer.echo(f"Merging {from_display} → {to_display}")
    typer.echo("✓ Merged")


@app.command("delete")
def delete_agent(
    agent_ref: str, force: bool = typer.Option(False, "--force", help="Skip confirmation")
):
    """Hard delete an agent and all related data. Use with caution - backups required."""
    result = _resolve_agent_id(agent_ref)

    if not result:
        typer.echo(f"Error: Agent not found for '{agent_ref}'")
        raise typer.Exit(1)

    agent_id, display_name = result

    if not force:
        typer.echo(f"⚠️  About to permanently delete: {display_name}")
        typer.echo("This will remove all data from:")
        typer.echo("  - agents table")
        typer.echo("  - memories table")
        typer.echo("  - events table")
        typer.echo("Ensure backups exist before proceeding.")
        if not typer.confirm("Continue?"):
            typer.echo("Cancelled.")
            return

    with api.connect() as conn:
        conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))

    typer.echo(f"✓ Deleted {display_name}")


@app.command("rename")
def rename(old_name: str, new_name: str):
    """Rename an agent."""
    try:
        if api.rename_agent(old_name, new_name):
            typer.echo(f"✓ Renamed {old_name} → {new_name}")
        else:
            typer.echo(f"❌ Agent not found: {old_name}. Run `spawn` to list agents.", err=True)
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


def _resolve_agent_id(agent_ref: str) -> tuple[str, str] | None:
    """Resolve agent ref to (agent_id, display_name)."""
    if len(agent_ref) == 36 and agent_ref.count("-") == 4:
        name = api.get_agent_name(agent_ref)
        if name:
            return agent_ref, name
        return None
    agent_id = api.get_agent_id(agent_ref)
    if agent_id:
        return agent_id, agent_ref
    return None
