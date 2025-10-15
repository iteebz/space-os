import functools

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
