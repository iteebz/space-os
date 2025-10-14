import typer

from ..spawn import registry

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main(
    ctx: typer.Context,
):
    """Show agents with self-descriptions and s/b/m/k ladder."""
    if ctx.invoked_subcommand is not None:
        return

    _show_agents()


def _show_agents():
    registry.init_db()

    from ..lib import stats as stats_lib

    metrics = stats_lib.get_agent_metrics()

    with registry.get_db() as conn:
        agents = conn.execute(
            "SELECT id, name, self_description FROM agents WHERE archived_at IS NULL ORDER BY name"
        ).fetchall()

        typer.echo(f"{'NAME':<20} {'S/B/M/K':<15} {'SELF'}")
        typer.echo("-" * 80)

        for agent in agents:
            name = agent["name"] or "(unnamed)"
            full_self_desc = agent["self_description"] or "-"

            agent_id = agent["id"]
            m = metrics.get(agent_id, {"spawns": 0, "msgs": 0, "mems": 0, "knowledge": 0})
            sbmk = f"{m['spawns']}/{m['msgs']}/{m['mems']}/{m['knowledge']}"

            typer.echo(f"{name:<20} {sbmk:<15} {full_self_desc}")

        typer.echo()
        typer.echo(f"Total: {len(agents)}")


@app.command()
def list():
    """Alias for default command."""
    _show_agents()


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
