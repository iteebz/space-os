import json


def constitute_identity(identity: str):
    """Hash constitution and emit provenance event for bridge operations."""
    from .. import events
    from ..spawn import registry, spawn

    role = _extract_role(identity)
    if not role:
        return

    try:
        registry.init_db()
        cfg = spawn.load_config()
        if role not in cfg["roles"]:
            return

        const_path = spawn.get_constitution_path(role)
        base_constitution = const_path.read_text()
        agent_name = _extract_role(identity)  # Extract agent_name
        full_identity = spawn.inject_identity(
            base_constitution, role, agent_name, model=_extract_model_from_identity(identity)
        )
        const_hash = spawn.hash_content(full_identity)
        registry.save_constitution(const_hash, full_identity)

        agent_id = registry.ensure_agent(identity)
        model = _extract_model_from_identity(identity)
        events.emit(
            "bridge",
            "constitution_invoked",
            agent_id,
            json.dumps({"constitution_hash": const_hash, "role": role, "model": model}),
        )
    except (FileNotFoundError, ValueError):
        pass


def _extract_role(identity: str) -> str | None:
    """Extract role from identity like zealot-1 -> zealot."""
    if "-" in identity:
        return identity.rsplit("-", 1)[0]
    return identity


def _extract_model_from_identity(identity: str) -> str | None:
    """Extract model name from spawn config based on identity."""
    from ..spawn import spawn

    role = _extract_role(identity)
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
