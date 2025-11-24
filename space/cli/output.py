import json as json_lib

import typer


def init_context(
    ctx: typer.Context,
    json_output: bool = False,
    quiet_output: bool = False,
    identity: str | None = None,
) -> None:
    """Initialize CLI context with standard flags and identity."""
    if ctx.obj is None or not isinstance(ctx.obj, dict):
        ctx.obj = {}
    ctx.obj["json_output"] = json_output
    ctx.obj["quiet_output"] = quiet_output
    ctx.obj["identity"] = identity


def out_json(data: dict) -> str:
    return json_lib.dumps(data, indent=2)


def out_text(msg: str, ctx_obj: dict | None = None) -> None:
    if ctx_obj and ctx_obj.get("quiet_output"):
        return
    typer.echo(msg)


def show_sync_progress(event) -> None:
    typer.echo(f"  {event.provider:<10} {event.discovered:<12} {event.synced}")


def is_json_mode(ctx: typer.Context) -> bool:
    """Check if JSON output mode is enabled."""
    return ctx.obj.get("json_output", False) if ctx.obj else False


def is_quiet_mode(ctx: typer.Context) -> bool:
    """Check if quiet output mode is enabled."""
    return ctx.obj.get("quiet_output", False) if ctx.obj else False


def echo_json(data, ctx: typer.Context) -> bool:
    """Output data as JSON if in JSON mode. Returns True if output, False otherwise."""
    if is_json_mode(ctx):
        typer.echo(json_lib.dumps(data, indent=2))
        return True
    return False


def echo_text(msg: str, ctx: typer.Context) -> None:
    """Echo message only if not in quiet mode."""
    if not is_quiet_mode(ctx):
        typer.echo(msg)
