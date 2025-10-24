import typer

from space.apps import stats as stats_lib

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def list_agents(show_all: bool = typer.Option(False, "--all", help="Show archived agents")):
    """List all agents (registered and orphaned across universe)."""
    from space.os.core.spawn import db as spawn_db

    stats = stats_lib.agent_stats(include_archived=show_all) or []

    if not stats:
        typer.echo("No agents found.")
        return

    with spawn_db.connect() as conn:
        {row["agent_id"]: row["name"] for row in conn.execute("SELECT agent_id, name FROM agents")}

    typer.echo(f"{'NAME':<20} {'ID':<10} {'E-S-B-M-K':<20} {'SELF'}")
    typer.echo("-" * 100)

    for s in sorted(stats, key=lambda a: a.agent_name):
        name = s.agent_name
        agent_id = s.agent_id
        short_id = agent_id[:8]

        if len(name) == 36 and name.count("-") == 4:
            resolved = spawn_db.get_identity(name)
            if resolved:
                name = resolved

        desc = "-"
        esbmk = f"{s.events}-{s.spawns}-{s.msgs}-{s.mems}-{s.knowledge}"

        typer.echo(f"{name:<20} {short_id:<10} {esbmk:<20} {desc}")

    typer.echo()
    typer.echo(f"Total: {len(stats)}")
