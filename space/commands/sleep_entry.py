from .sleep import sleep


def main():
    """Entry point for standalone sleep command."""
    import typer

    app = typer.Typer()
    app.command()(sleep)
    app()
