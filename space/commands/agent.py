import time

import typer

from space import events as events_lib
from space.lib import stats as stats_lib
from space.spawn import registry

app = typer.Typer(invoke_without_command=True)


def _resolve_agent_id(fuzzy_match: str) -> tuple[str, str] | None:
    """Resolve agent ID from partial UUID or identity name. Returns (agent_id, display_name)."""
    registry.init_db()
    
    with registry.get_db() as conn:
        rows = conn.execute(
            "SELECT id, name FROM agents WHERE archived_at IS NULL"
        ).fetchall()
    
    candidates = []
    for row in rows:
        agent_id = row["id"]
        name = row["name"]
        
        if agent_id.startswith(fuzzy_match):
            candidates.append((agent_id, name))
        elif name and name.lower() == fuzzy_match.lower():
            candidates.append((agent_id, name))
    
    if len(candidates) == 1:
        agent_id, name = candidates[0]
        resolved = registry.get_identity(name) if (name and len(name) == 36 and name.count("-") == 4) else name
        return (agent_id, resolved or name or agent_id[:8])
    
    return None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
):
    if ctx.invoked_subcommand is None:
        list_agents()


@app.command("list")
def list_agents():
    """List all registered agents."""

    registry.init_db()

    with registry.get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, self_description FROM agents WHERE archived_at IS NULL ORDER BY name"
        ).fetchall()

        if not rows:
            typer.echo("No agents registered.")
            return

        stats = stats_lib.agent_stats() or []
        stats_by_id = {s.agent_id: s for s in stats}

        typer.echo(f"{'NAME':<20} {'ID':<10} {'S/B/M/K':<15} {'SELF'}")
        typer.echo("-" * 90)

        for row in rows:
            name = row["name"] or "(unnamed)"
            agent_id = row["id"]
            short_id = agent_id[:8]
            
            if len(name) == 36 and name.count("-") == 4:
                resolved = registry.get_identity(name)
                if resolved:
                    name = resolved

            desc = row["self_description"] or "-"
            s = stats_by_id.get(agent_id)
            if s:
                sbmk = f"{s.spawns}/{s.msgs}/{s.mems}/{s.knowledge}"
            else:
                sbmk = "0/0/0/0"

            typer.echo(f"{name:<20} {short_id:<10} {sbmk:<15} {desc}")

        typer.echo()
        typer.echo(f"Total: {len(rows)}")


@app.command("inspect")
def inspect_agent(agent_ref: str):
    """Inspect agent activity and state."""
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
