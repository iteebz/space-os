import typer

from space.lib import stats as stats_lib
from space.spawn import registry

app = typer.Typer(invoke_without_command=True)


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

        typer.echo(f"{'NAME':<20} {'S/B/M/K':<15} {'SELF'}")
        typer.echo("-" * 80)

        for row in rows:
            name = row["name"] or "(unnamed)"
            if len(name) == 36 and name.count("-") == 4:
                resolved = registry.get_identity(name)
                if resolved:
                    name = resolved

            desc = row["self_description"] or "-"
            s = stats_by_id.get(row["id"])
            if s:
                sbmk = f"{s.spawns}/{s.msgs}/{s.mems}/{s.knowledge}"
            else:
                sbmk = "0/0/0/0"

            typer.echo(f"{name:<20} {sbmk:<15} {desc}")

        typer.echo()
        typer.echo(f"Total: {len(rows)}")
