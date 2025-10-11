import typer

from ..spawn import registry

app = typer.Typer()


@app.command()
def list(
    all: bool = typer.Option(False, "--all", help="Show all agents including duplicates"),
    stats: bool = typer.Option(False, "--stats", "-s", help="Show activity stats"),
    archived: bool = typer.Option(False, "--archived", help="Show archived agents"),
):
    """List agents."""
    registry.init_db()

    from datetime import datetime

    from ..lib import db, paths
    from ..lib import stats as stats_lib

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
                    activity[row[0]] = {"first_spawn": row[1], "last_spawn": row[2]}

        metrics = stats_lib.get_agent_metrics()

    with registry.get_db() as conn:
        archive_filter = "" if archived else "WHERE archived_at IS NULL"
        
        if all:
            agents = conn.execute(
                f"SELECT id, name FROM agents {archive_filter} ORDER BY name, created_at"
            ).fetchall()

            if stats:
                typer.echo(
                    f"{'NAME':<20} {'ID':<38} {'FIRST':<12} {'LAST':<12} {'S-B-M-K':<15}"
                )
                typer.echo("-" * 110)
            else:
                typer.echo(f"{'NAME':<30} {'ID':<38}")
                typer.echo("-" * 80)

            for agent in agents:
                name = agent["name"] or "(unnamed)"
                agent_id = agent["id"]

                if stats:
                    act = activity.get(agent_id, {})
                    first = (
                        datetime.fromtimestamp(act["first_spawn"]).strftime("%Y-%m-%d")
                        if act.get("first_spawn")
                        else "-"
                    )
                    last = (
                        datetime.fromtimestamp(act["last_spawn"]).strftime("%Y-%m-%d")
                        if act.get("last_spawn")
                        else "-"
                    )

                    m = metrics.get(agent_id, {"spawns": 0, "msgs": 0, "mems": 0, "knowledge": 0})
                    sbmk = f"{m['spawns']}-{m['msgs']}-{m['mems']}-{m['knowledge']}"

                    typer.echo(
                        f"{name:<20} {agent_id} {first:<12} {last:<12} {sbmk:<15}"
                    )
                else:
                    typer.echo(f"{name:<30} {agent_id}")

            typer.echo()
            typer.echo(f"Total: {len(agents)}")
        else:
            unique_agents = conn.execute(
                f"SELECT name, COUNT(*) as count FROM agents {archive_filter} GROUP BY name ORDER BY name"
            ).fetchall()

            if stats:
                typer.echo(
                    f"{'NAME':<20} {'COUNT':<8} {'FIRST':<12} {'LAST':<12} {'S-B-M-K':<15}"
                )
                typer.echo("-" * 110)
            else:
                typer.echo(f"{'NAME':<30} {'COUNT':<8}")
                typer.echo("-" * 50)

            for row in unique_agents:
                name = row["name"] or "(unnamed)"
                count = row["count"]
                
                agent_ids = registry.get_agent_ids(name, include_archived=archived)

                if stats:
                    total_metrics = {"spawns": 0, "msgs": 0, "mems": 0, "knowledge": 0}
                    first_spawn = None
                    last_spawn = None
                    
                    for agent_id in agent_ids:
                        act = activity.get(agent_id, {})
                        if act.get("first_spawn"):
                            if not first_spawn or act["first_spawn"] < first_spawn:
                                first_spawn = act["first_spawn"]
                        if act.get("last_spawn"):
                            if not last_spawn or act["last_spawn"] > last_spawn:
                                last_spawn = act["last_spawn"]
                        
                        m = metrics.get(agent_id, {"spawns": 0, "msgs": 0, "mems": 0, "knowledge": 0})
                        total_metrics["spawns"] += m["spawns"]
                        total_metrics["msgs"] += m["msgs"]
                        total_metrics["mems"] += m["mems"]
                        total_metrics["knowledge"] += m["knowledge"]
                    
                    first = datetime.fromtimestamp(first_spawn).strftime("%Y-%m-%d") if first_spawn else "-"
                    last = datetime.fromtimestamp(last_spawn).strftime("%Y-%m-%d") if last_spawn else "-"
                    sbmk = f"{total_metrics['spawns']}-{total_metrics['msgs']}-{total_metrics['mems']}-{total_metrics['knowledge']}"

                    typer.echo(
                        f"{name:<20} {count:<8} {first:<12} {last:<12} {sbmk:<15}"
                    )
                else:
                    typer.echo(f"{name:<30} {count:<8}")

            typer.echo()
            typer.echo(f"Total unique names: {len(unique_agents)}")


@app.command()
def rename(
    old_name: str = typer.Argument(..., help="Current agent name"),
    new_name: str = typer.Argument(..., help="New agent name"),
):
    """Rename an agent (merges with existing if new_name exists)."""
    registry.init_db()

    success = registry.rename_agent(old_name, new_name)
    if success:
        typer.echo(f"Renamed {old_name} → {new_name}")
    else:
        typer.echo(f"Agent {old_name} not found")
        raise typer.Exit(1)


@app.command()
def archive(
    name: str = typer.Argument(..., help="Agent name to archive"),
):
    """Archive an agent."""
    registry.init_db()
    
    if registry.archive_agent(name):
        typer.echo(f"Archived {name}")
    else:
        typer.echo(f"Agent {name} not found")
        raise typer.Exit(1)


@app.command()
def restore(
    name: str = typer.Argument(..., help="Agent name to restore"),
):
    """Restore an archived agent."""
    registry.init_db()
    
    if registry.restore_agent(name):
        typer.echo(f"Restored {name}")
    else:
        typer.echo(f"Agent {name} not found")
        raise typer.Exit(1)


@app.command()
def show(
    name: str = typer.Argument(..., help="Agent name"),
):
    """Show agent details."""
    registry.init_db()

    agent_ids = registry.get_agent_ids(name, include_archived=True)
    if not agent_ids:
        typer.echo(f"Agent {name} not found")
        raise typer.Exit(1)

    typer.echo(f"Name: {name}")
    typer.echo(f"Instances: {len(agent_ids)}")
    
    with registry.get_db() as conn:
        for agent_id in agent_ids:
            agent = conn.execute(
                "SELECT id, self_description, archived_at FROM agents WHERE id = ?", (agent_id,)
            ).fetchone()
            
            status = "archived" if agent["archived_at"] else "active"
            typer.echo(f"\n  [{status}] {agent['id']}")
            if agent["self_description"]:
                typer.echo(f"    {agent['self_description']}")


@app.command()
def merge(
    from_agent: str = typer.Argument(..., help="Source agent (name or UUID)"),
    to_agent: str = typer.Argument(..., help="Target agent (name or UUID)"),
):
    """Merge agent histories from source to target."""
    registry.init_db()
    
    if registry.merge_agents(from_agent, to_agent):
        typer.echo(f"Merged {from_agent} → {to_agent}")
    else:
        typer.echo("Merge failed")
        raise typer.Exit(1)
