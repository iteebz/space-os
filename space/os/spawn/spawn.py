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
