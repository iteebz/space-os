import typer

from space.os.spawn import db as spawn_db

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        show_registry()


@app.command("show")
def show_registry():
    """Show constitutional registry: constitutional evolution provenance.

    The registry tracks all constitutional versions by hash, enabling complete
    provenance of agent personality and instruction changes over time. Each
    constitution is content-addressable via its hash, creating an immutable
    audit trail of constitutional evolution.
    """
    pass

    with spawn_db.connect() as conn:
        rows = conn.execute(
            "SELECT hash, content, created_at FROM constitutions ORDER BY created_at DESC"
        ).fetchall()

        if not rows:
            typer.echo("Registry empty.")
            return

        typer.echo("CONSTITUTIONAL REGISTRY - Provenance of Agent Personality Evolution")
        typer.echo("=" * 80)
        typer.echo()

        for row in rows:
            hash_val = row["hash"]
            content = row["content"]
            created = row["created_at"]

            lines = content.split("\n")
            first_line = lines[0][:60] if lines else "(empty)"
            line_count = len(lines)

            typer.echo(f"Hash:     {hash_val}")
            typer.echo(f"Created:  {created}")
            typer.echo(f"Lines:    {line_count}")
            typer.echo(f"Preview:  {first_line}")
            typer.echo()


@app.command("backfill")
def backfill():
    """Backfill orphaned agent IDs from bridge into spawn_db."""
    pass
    count = spawn_db.backfill_unknown_agents()
    if count > 0:
        typer.echo(f"Registered {count} orphaned agent(s)")
    else:
        typer.echo("No orphaned agents found")
