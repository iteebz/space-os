from space import config


def resolve_model_alias(alias: str) -> str:
    """Resolve model alias to full model name."""
    config.init_config()
    cfg = config.load_config()
    aliases = cfg.get("model_aliases", {})
    return aliases.get(alias, alias)


def build_identity_prompt(identity: str, model: str | None = None) -> str:
    """Build identity and space instructions for first prompt injection."""
    parts = [f"You are {identity}."]
    if model:
        parts[0] += f" Your model is {model}."
    parts.append("")
    parts.append("space commands:")
    parts.append("  run `space` for orientation (already in PATH)")
    parts.append(f"  run `memory --as {identity}` to access memories")
    return "\n".join(parts)
