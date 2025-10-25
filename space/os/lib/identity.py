"""Agent role instance helpers for space commands."""

import json

import typer


def callback_with_role(
    ctx: typer.Context,
    role: str = typer.Option(None, "--as", help="Agent role instance (e.g., zealot-1)"),
    **extra_ctx,
):
    """Standard callback that captures --as and stores in ctx.obj."""
    ctx.obj = ctx.obj or {}
    ctx.obj["role"] = role
    ctx.obj.update(extra_ctx)

    if role:
        from .. import events
        from ..core.spawn import db as spawn_db

        command = ctx.info_name or "unknown"
        agent_id = spawn_db.ensure_agent(role)
        events.emit("role", command, agent_id)


def require_role(ctx: typer.Context, role: str | None = None) -> str:
    """Get role instance from command arg or ctx.obj, error if missing."""
    resolved = role or (ctx.obj or {}).get("role")
    if not resolved:
        typer.echo("Error: --as <role> required", err=True)
        raise typer.Exit(1)
    return resolved


def get_role(ctx: typer.Context, role: str | None = None) -> str | None:
    """Get role instance from command arg or ctx.obj, return None if missing."""
    return role or (ctx.obj or {}).get("role")


def _get_constitution_and_config(role: str) -> tuple[str, dict] | None:
    from .. import config

    constitution = extract_constitution(role)
    if not constitution:
        return None

    config.init_config()
    cfg = config.load_config()
    if constitution not in cfg["roles"]:
        return None
    return constitution, cfg


def emit_constitution_invoked(role: str):
    """Emit constitution invoked event (versioning via git)."""
    from .. import events
    from ..core.spawn import db as spawn_db

    result = _get_constitution_and_config(role)
    if not result:
        return
    constitution, cfg = result

    agent_id = spawn_db.ensure_agent(role)
    model = extract_model_from_role(role, cfg)
    events.emit(
        "bridge",
        "constitution_invoked",
        agent_id,
        json.dumps({"role": constitution, "model": model}),
    )


def extract_constitution(role: str) -> str | None:
    """Extract constitutional role from agent instance like zealot-1 -> zealot."""
    if "-" in role:
        return role.rsplit("-", 1)[0]
    return role


def extract_model_from_role(role: str, cfg: dict) -> str | None:
    """Extract model name from spawn config based on role."""
    constitution = extract_constitution(role)
    if not constitution:
        return None

    if constitution in cfg["roles"]:
        base_agent = cfg["roles"][constitution].get("base_agent")
        if base_agent and "agents" in cfg:
            agent_cfg = cfg["agents"].get(base_agent, {})
            return agent_cfg.get("model")

    return None
