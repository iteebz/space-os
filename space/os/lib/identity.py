"""Identity-aware CLI helpers for space commands."""

import json

import typer


def callback_with_identity(
    ctx: typer.Context,
    identity: str = typer.Option(None, "--as", help="Identity name"),
    **extra_ctx,
):
    """Standard callback that captures --as and stores in ctx.obj."""
    ctx.obj = ctx.obj or {}
    ctx.obj["identity"] = identity
    ctx.obj.update(extra_ctx)

    if identity:
        from .. import events
        from ..core.spawn import db as spawn_db

        command = ctx.info_name or "unknown"
        agent_id = spawn_db.ensure_agent(identity)
        events.emit("identity", command, agent_id)


def require_identity(ctx: typer.Context, identity: str | None = None) -> str:
    """Get identity from command arg or ctx.obj, error if missing."""
    resolved = identity or (ctx.obj or {}).get("identity")
    if not resolved:
        typer.echo("Error: --as <identity> required", err=True)
        raise typer.Exit(1)
    return resolved


def get_identity(ctx: typer.Context, identity: str | None = None) -> str | None:
    """Get identity from command arg or ctx.obj, return None if missing."""
    return identity or (ctx.obj or {}).get("identity")


def _get_role_and_config(identity: str) -> tuple[str, dict] | None:
    from .. import config

    role = extract_role(identity)
    if not role:
        return None

    pass
    config.init_config()
    cfg = config.load_config()
    if role not in cfg["roles"]:
        return None
    return role, cfg


def _process_constitution(role: str) -> tuple[str, str]:
    from ..core.spawn import db as spawn_db
    from ..core.spawn.spawn import get_constitution_path, hash_content

    const_path = get_constitution_path(role)
    final_constitution_content = const_path.read_text()
    const_hash = hash_content(final_constitution_content)
    spawn_db.save_constitution(const_hash, final_constitution_content)
    return const_hash, final_constitution_content


def constitute_identity(identity: str):
    """Hash constitution and emit provenance event."""
    from .. import events
    from ..core.spawn import db as spawn_db

    result = _get_role_and_config(identity)
    if not result:
        return
    role, cfg = result

    const_hash, _ = _process_constitution(role)

    agent_id = spawn_db.ensure_agent(identity)
    model = extract_model_from_identity(identity, cfg)
    events.emit(
        "bridge",
        "constitution_invoked",
        agent_id,
        json.dumps({"constitution_hash": const_hash, "role": role, "model": model}),
    )


def extract_role(identity: str) -> str | None:
    """Extract role from identity like zealot-1 -> zealot."""
    if "-" in identity:
        return identity.rsplit("-", 1)[0]
    return identity


def extract_model_from_identity(identity: str, cfg: dict) -> str | None:
    """Extract model name from spawn config based on identity."""
    role = extract_role(identity)
    if not role:
        return None

    if role in cfg["roles"]:
        base_identity = cfg["roles"][role].get("base_identity")
        if base_identity and "agents" in cfg:
            agent_cfg = cfg["agents"].get(base_identity, {})
            return agent_cfg.get("model")

    return None
