from .wake import wake


def main():
    """Entry point for standalone wake command."""
    import typer
    app = typer.Typer()
    app.command()(wake)
    app()
