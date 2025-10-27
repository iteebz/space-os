import typer

from space.apps.health import api

app = typer.Typer()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(health)


@app.command()
def health():
    """Verify space-os lattice integrity."""
    issues, counts_by_db = api.run_all_checks()

    for db_name, tables_counts in counts_by_db.items():
        for tbl, cnt in tables_counts.items():
            typer.echo(f"✓ {db_name}::{tbl} ({cnt} rows)")

    if issues:
        for issue in issues:
            typer.echo(issue)
        raise typer.Exit(1)

    typer.echo("\n✓ Space infrastructure healthy")


def main() -> None:
    """Entry point for poetry script."""
    app()
