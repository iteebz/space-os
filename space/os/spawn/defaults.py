"""Spawn default identities and models."""

DEFAULT_MODEL = "claude-haiku-4-5"

DEFAULT_AGENT_MODELS: dict[str, str] = {
    "zealot": DEFAULT_MODEL,
    "sentinel": "gemini-2.5-pro",
    "crucible": "gpt-5-codex",
}


def canonical_model(identity: str) -> str:
    """Return canonical model for identity, falling back to DEFAULT_MODEL."""

    return DEFAULT_AGENT_MODELS.get(identity, DEFAULT_MODEL)
