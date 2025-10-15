import json as json_lib

import typer

from space import events


def set_flags(ctx: typer.Context, json_output: bool = False, quiet_output: bool = False) -> None:
    """Set output flags in context."""
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["json_output"] = json_output
    ctx.obj["quiet_output"] = quiet_output


def out_json(data: dict) -> str:
    """Format dict as JSON string."""
    return json_lib.dumps(data, indent=2)


def out_text(msg: str, ctx_obj: dict | None = None) -> None:
    """Echo text unless quiet mode."""
    if ctx_obj and ctx_obj.get("quiet_output"):
        return
    typer.echo(msg)


def emit_error(module: str, agent_id: str | None, cmd: str, exc: Exception | str) -> None:
    """Standardized error event emission."""
    detail = str(exc) if isinstance(exc, Exception) else exc
    events.emit(module, "error", agent_id or "", f"{cmd}: {detail}")
