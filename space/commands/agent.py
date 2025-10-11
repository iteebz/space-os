import typer

from ..spawn import canonical, registry

app = typer.Typer()


@app.command()
def list(
    all: bool = typer.Option(False, "--all", help="Show all agents including orphans"),
    stats: bool = typer.Option(False, "--stats", "-s", help="Show activity stats"),
):
    """List canonical agents with aliases."""
    registry.init_db()
    
    from ..lib import db, paths, stats as stats_lib
    from datetime import datetime
    
    activity = {}
    metrics = {}
    
    if stats:
        events_db = paths.space_root() / "events.db"
        if events_db.exists():
            with db.connect(events_db) as conn:
                rows = conn.execute("""
                    SELECT agent_id, 
                           MIN(timestamp) as first_spawn,
                           MAX(timestamp) as last_spawn
                    FROM events 
                    GROUP BY agent_id
                """).fetchall()
                for row in rows:
                    activity[row[0]] = {
                        "first_spawn": row[1],
                        "last_spawn": row[2]
                    }
        
        metrics = stats_lib.get_agent_metrics()
    
    with registry.get_db() as conn:
        if all:
            agents = conn.execute(
                "SELECT id, name, canonical_id FROM agents ORDER BY canonical_id IS NULL DESC, name"
            ).fetchall()
            
            if stats:
                typer.echo(f"{'NAME':<20} {'ID':<38} {'FIRST':<12} {'LAST':<12} {'S-B-M-K':<15} {'STATUS'}")
                typer.echo("-" * 130)
            else:
                typer.echo(f"{'NAME':<30} {'ID':<38} {'STATUS'}")
                typer.echo("-" * 100)
            
            for agent in agents:
                name = agent["name"] or "(unnamed)"
                agent_id = agent["id"]
                canonical_id = agent["canonical_id"]
                
                if stats:
                    act = activity.get(agent_id, {})
                    first = datetime.fromtimestamp(act["first_spawn"]).strftime("%Y-%m-%d") if act.get("first_spawn") else "-"
                    last = datetime.fromtimestamp(act["last_spawn"]).strftime("%Y-%m-%d") if act.get("last_spawn") else "-"
                    
                    m = metrics.get(agent_id, {"spawns": 0, "msgs": 0, "mems": 0, "knowledge": 0})
                    sbmk = f"{m['spawns']}-{m['msgs']}-{m['mems']}-{m['knowledge']}"
                    
                    if canonical_id:
                        typer.echo(f"{name:<20} {agent_id} {first:<12} {last:<12} {sbmk:<15} → {canonical_id}")
                    else:
                        aliases = canonical.get_aliases(agent_id)
                        alias_str = f"aliases: {', '.join(aliases)}" if aliases else "canonical"
                        typer.echo(f"{name:<20} {agent_id} {first:<12} {last:<12} {sbmk:<15} {alias_str}")
                else:
                    if canonical_id:
                        typer.echo(f"{name:<30} {agent_id} → {canonical_id}")
                    else:
                        aliases = canonical.get_aliases(agent_id)
                        alias_str = f"aliases: {', '.join(aliases)}" if aliases else "canonical"
                        typer.echo(f"{name:<30} {agent_id} {alias_str}")
            
            typer.echo()
            typer.echo(f"Total: {len(agents)}")
        else:
            canonical_agents = conn.execute(
                "SELECT id, name FROM agents WHERE canonical_id IS NULL ORDER BY name"
            ).fetchall()
            
            if stats:
                typer.echo(f"{'NAME':<20} {'ID':<38} {'FIRST':<12} {'LAST':<12} {'S-B-M-K':<15} {'ALIASES'}")
                typer.echo("-" * 130)
            else:
                typer.echo(f"{'NAME':<30} {'ID':<38} {'ALIASES'}")
                typer.echo("-" * 100)
            
            for agent in canonical_agents:
                name = agent["name"] or "(unnamed)"
                agent_id = agent["id"]
                aliases = canonical.get_aliases(agent_id)
                alias_str = ", ".join(aliases) if aliases else ""
                
                if stats:
                    act = activity.get(agent_id, {})
                    first = datetime.fromtimestamp(act["first_spawn"]).strftime("%Y-%m-%d") if act.get("first_spawn") else "-"
                    last = datetime.fromtimestamp(act["last_spawn"]).strftime("%Y-%m-%d") if act.get("last_spawn") else "-"
                    
                    m = metrics.get(agent_id, {"spawns": 0, "msgs": 0, "mems": 0, "knowledge": 0})
                    sbmk = f"{m['spawns']}-{m['msgs']}-{m['mems']}-{m['knowledge']}"
                    
                    typer.echo(f"{name:<20} {agent_id} {first:<12} {last:<12} {sbmk:<15} {alias_str}")
                else:
                    typer.echo(f"{name:<30} {agent_id} {alias_str}")
            
            typer.echo()
            typer.echo(f"Total canonical agents: {len(canonical_agents)}")


@app.command()
def link(
    orphan_id: str = typer.Argument(..., help="Orphan agent ID to link"),
    canonical_id: str = typer.Argument(..., help="Canonical agent ID to link to"),
):
    """Link orphan agent ID to canonical identity."""
    registry.init_db()
    
    with registry.get_db() as conn:
        orphan = conn.execute("SELECT id, name FROM agents WHERE id = ?", (orphan_id,)).fetchone()
        if not orphan:
            typer.echo(f"Orphan agent {orphan_id} not found")
            raise typer.Exit(1)
        
        canonical_agent = conn.execute("SELECT id, name FROM agents WHERE id = ?", (canonical_id,)).fetchone()
        if not canonical_agent:
            typer.echo(f"Canonical agent {canonical_id} not found")
            raise typer.Exit(1)
    
    canonical.set_canonical(orphan_id, canonical_id)
    typer.echo(f"Linked {orphan['name'] or orphan_id} → {canonical_agent['name'] or canonical_id}")


@app.command()
def rename(
    old_name: str = typer.Argument(..., help="Current agent name"),
    new_name: str = typer.Argument(..., help="New agent name"),
):
    """Rename an agent."""
    registry.init_db()
    
    success = registry.rename_agent(old_name, new_name)
    if success:
        typer.echo(f"Renamed {old_name} → {new_name}")
    else:
        typer.echo(f"Agent {old_name} not found")
        raise typer.Exit(1)


@app.command()
def alias(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    alias_name: str = typer.Argument(..., help="Alias to add"),
):
    """Add alias for agent."""
    registry.init_db()
    
    with registry.get_db() as conn:
        agent = conn.execute("SELECT id, name FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if not agent:
            typer.echo(f"Agent {agent_id} not found")
            raise typer.Exit(1)
    
    canonical.add_alias(agent_id, alias_name)
    typer.echo(f"Added alias '{alias_name}' for {agent['name'] or agent_id}")


@app.command()
def show(
    name: str = typer.Argument(..., help="Agent name or alias"),
):
    """Show agent details."""
    registry.init_db()
    
    agent_id = registry.get_agent_id(name)
    if not agent_id:
        typer.echo(f"Agent {name} not found")
        raise typer.Exit(1)
    
    with registry.get_db() as conn:
        agent = conn.execute(
            "SELECT id, name, self_description, canonical_id FROM agents WHERE id = ?",
            (agent_id,)
        ).fetchone()
        
        typer.echo(f"ID: {agent['id']}")
        typer.echo(f"Name: {agent['name'] or '(unnamed)'}")
        if agent['self_description']:
            typer.echo(f"Self: {agent['self_description']}")
        if agent['canonical_id']:
            canonical_agent = conn.execute(
                "SELECT name FROM agents WHERE id = ?", (agent['canonical_id'],)
            ).fetchone()
            typer.echo(f"Canonical: {canonical_agent['name'] or agent['canonical_id']}")
        
        aliases = canonical.get_aliases(agent_id)
        if aliases:
            typer.echo(f"Aliases: {', '.join(aliases)}")
