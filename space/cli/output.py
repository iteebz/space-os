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


def set_flags(ctx: typer.Context, json_output: bool = False, quiet_output: bool = False) -> None:
    """Deprecated: use init_context instead."""
    init_context(ctx, json_output, quiet_output)


def out_json(data: dict) -> str:
    return json_lib.dumps(data, indent=2)


def out_text(msg: str, ctx_obj: dict | None = None) -> None:
    if ctx_obj and ctx_obj.get("quiet_output"):
        return
    typer.echo(msg)


def emit_error(module: str, agent_id: str | None, cmd: str, exc: Exception | str) -> None:
    str(exc) if isinstance(exc, Exception) else exc


def show_sync_progress(event) -> None:
    typer.echo(f"  {event.provider:<10} {event.discovered:<12} {event.synced}")
