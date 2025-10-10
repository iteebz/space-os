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


def constitute_identity(identity: str):
    """Hash constitution and emit provenance event."""
    from .. import events
    from ..spawn import registry, spawn

    role = extract_role(identity)
    if not role:
        return

    try:
        registry.init_db()
        cfg = spawn.load_config()
        if role not in cfg["roles"]:
            return

        const_path = spawn.get_constitution_path(role)
        base_constitution = const_path.read_text()
        full_identity = spawn.inject_identity(base_constitution, identity)
        const_hash = spawn.hash_content(full_identity)
        registry.save_constitution(const_hash, full_identity)

        model = extract_model_from_identity(identity)
        events.emit(
            "memory",
            "constitution_invoked",
            identity,
            json.dumps({"constitution_hash": const_hash, "role": role, "model": model}),
        )
    except (FileNotFoundError, ValueError):
        pass


def extract_role(identity: str) -> str | None:
    """Extract role from identity like zealot-1 -> zealot."""
    if "-" in identity:
        return identity.rsplit("-", 1)[0]
    return identity


def extract_model_from_identity(identity: str) -> str | None:
    """Extract model name from spawn config based on identity."""
    from ..spawn import spawn

    role = extract_role(identity)
    if not role:
        return None

    try:
        cfg = spawn.load_config()
        if role in cfg["roles"]:
            base_identity = cfg["roles"][role].get("base_identity")
            if base_identity and "agents" in cfg:
                agent_cfg = cfg["agents"].get(base_identity, {})
                return agent_cfg.get("model")
    except (FileNotFoundError, ValueError, KeyError):
        pass

    return None
