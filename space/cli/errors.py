"""CLI error handling: wrap commands to report errors instead of silent failures."""

from functools import wraps

import typer
from click.exceptions import Exit


def error_feedback(f):
    """Wrap command to catch exceptions and report them before exiting.

    Catches common errors (ValueError, OSError, etc.) and echoes them to stderr
    before raising SystemExit(1). Prevents silent failures in CLI commands.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (SystemExit, Exit):
            raise
        except (ValueError, KeyError, TypeError) as e:
            typer.echo(f"Invalid input: {e}", err=True)
            raise typer.Exit(1) from e
        except OSError as e:
            typer.echo(f"File error: {e}", err=True)
            raise typer.Exit(1) from e
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from e

    return wrapper
