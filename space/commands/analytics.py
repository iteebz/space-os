import typer

from ..lib import db, paths
from ..spawn import canonical, registry


def analytics(
    resource: str = typer.Argument(..., help="Resource to analyze: agents, identities, canonical"),
):
    """Debug analytics for space infrastructure."""
    if resource in ("agents", "identities"):
        _show_agent_mappings()
    elif resource == "canonical":
        _show_canonical_agents()
    else:
        typer.echo(f"Unknown resource: {resource}")
        typer.echo("Available: agents, identities, canonical")


def _show_agent_mappings():
    """Show all agent IDs and their name mappings across databases."""
    registry.init_db()
    
    with registry.get_db() as conn:
        agents = conn.execute(
            "SELECT id, name, self_description, created_at FROM agents ORDER BY created_at DESC"
        ).fetchall()
    
    typer.echo(f"{'ID':<38} {'NAME':<20} {'SELF':<50} {'CREATED'}")
    typer.echo("-" * 130)
    
    for agent in agents:
        agent_id = agent[0]
        name = agent[1]
        self_desc = (agent[2][:47] + "...") if agent[2] and len(agent[2]) > 50 else (agent[2] or "")
        created = agent[3]
        typer.echo(f"{agent_id} {name:<20} {self_desc:<50} {created}")
    
    typer.echo()
    typer.echo(f"Total unique agents: {len(agents)}")
    
    _show_usage_by_agent(agents)


def _show_usage_by_agent(agents: list):
    """Show event/message counts per agent."""
    bridge_db = paths.space_root() / "bridge.db"
    events_db = paths.space_root() / "events.db"
    
    usage = {}
    
    if bridge_db.exists():
        with db.connect(bridge_db) as conn:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) FROM messages GROUP BY agent_id"
            ).fetchall()
            for row in rows:
                usage[row[0]] = {"msgs": row[1], "spawns": 0}
    
    if events_db.exists():
        with db.connect(events_db) as conn:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) FROM events WHERE event_type = 'session_start' GROUP BY agent_id"
            ).fetchall()
            for row in rows:
                if row[0] in usage:
                    usage[row[0]]["spawns"] = row[1]
                else:
                    usage[row[0]] = {"msgs": 0, "spawns": row[1]}
    
    if usage:
        typer.echo()
        typer.echo(f"{'ID':<38} {'SPAWNS':<10} {'MESSAGES'}")
        typer.echo("-" * 60)
        
        for agent_id, counts in sorted(usage.items(), key=lambda x: x[1]["spawns"], reverse=True):
            typer.echo(f"{agent_id} {counts['spawns']:<10} {counts['msgs']}")


def _show_canonical_agents():
    """Show canonical agent hierarchy with aliases and linked IDs."""
    registry.init_db()
    agents = canonical.get_canonical_agents()
    
    bridge_db = paths.space_root() / "bridge.db"
    events_db = paths.space_root() / "events.db"
    
    usage = {}
    if bridge_db.exists():
        with db.connect(bridge_db) as conn:
            rows = conn.execute("SELECT agent_id, COUNT(*) FROM messages GROUP BY agent_id").fetchall()
            for row in rows:
                usage[row[0]] = {"msgs": row[1], "spawns": 0}
    
    if events_db.exists():
        with db.connect(events_db) as conn:
            rows = conn.execute(
                "SELECT agent_id, COUNT(*) FROM events WHERE event_type = 'session_start' GROUP BY agent_id"
            ).fetchall()
            for row in rows:
                if row[0] in usage:
                    usage[row[0]]["spawns"] = row[1]
                else:
                    usage[row[0]] = {"msgs": 0, "spawns": row[1]}
    
    typer.echo(f"{'CANONICAL NAME':<20} {'ID':<38} {'SPAWNS':<8} {'MSGS':<8} {'ALIASES'}")
    typer.echo("-" * 120)
    
    for agent in sorted(agents, key=lambda a: usage.get(a["id"], {}).get("spawns", 0), reverse=True):
        agent_id = agent["id"]
        name = agent["name"] or "(unnamed)"
        stats = usage.get(agent_id, {"spawns": 0, "msgs": 0})
        aliases = ", ".join(agent["aliases"]) if agent["aliases"] else ""
        
        typer.echo(f"{name:<20} {agent_id} {stats['spawns']:<8} {stats['msgs']:<8} {aliases}")
        
        for linked_id in agent["linked_ids"]:
            linked_stats = usage.get(linked_id, {"spawns": 0, "msgs": 0})
            if linked_stats["spawns"] > 0 or linked_stats["msgs"] > 0:
                typer.echo(f"  └─ linked: {linked_id} {linked_stats['spawns']:<8} {linked_stats['msgs']:<8}")
    
    typer.echo()
    typer.echo(f"Total canonical identities: {len(agents)}")
