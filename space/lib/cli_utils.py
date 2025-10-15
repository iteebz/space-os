import functools
import json

import typer


def common_cli_options(f):
    """
    Decorator to add common CLI options like --json and --quiet to Typer commands.
    """
    @functools.wraps(f)
    def wrapper(
        ctx: typer.Context,
        json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
        quiet_output: bool = typer.Option(
            False, "--quiet", "-q", help="Suppress non-essential output."
        ),
        *args,
        **kwargs,
    ):
        ctx.obj = ctx.obj or {}
        ctx.obj["json_output"] = json_output
        ctx.obj["quiet_output"] = quiet_output
        return f(ctx, *args, **kwargs)
    return wrapper


def print_result(ctx: typer.Context, result, success_message: str = None, error_message: str = None):
    """
    Helper to print results based on json_output and quiet_output flags.
    """
    json_output = ctx.obj.get("json_output", False)
    quiet_output = ctx.obj.get("quiet_output", False)

    if json_output:
        typer.echo(json.dumps(result, indent=2))
    elif not quiet_output:
        if result.get("status") == "error":
            typer.echo(f"❌ {error_message or result.get('message', 'An error occurred.')}")
        else:
            typer.echo(success_message or result.get('message', 'Operation successful.'))
