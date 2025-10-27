"""Available models for different providers.

This module defines the models available for each provider CLI.
"""

from dataclasses import dataclass, field


@dataclass
class Model:
    """Model definition."""

    id: str
    name: str
    provider: str
    description: str = ""
    reasoning_levels: list[str] = field(default_factory=list)


CLAUDE_MODELS = [
    Model(
        id="claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        provider="claude",
        description="Latest and most intelligent model, best for complex agents and coding tasks",
    ),
    Model(
        id="claude-opus-4-1",
        name="Claude Opus 4.1",
        provider="claude",
        description="Maximum capability for complex development tasks",
    ),
    Model(
        id="claude-haiku-4-5",
        name="Claude Haiku 4.5",
        provider="claude",
        description="Lightweight with 90% capability at 3x lower cost",
    ),
]

CODEX_MODELS = [
    Model(
        id="gpt-5-codex",
        name="GPT-5 Codex",
        provider="codex",
        description="Optimized for agentic coding in Codex CLI",
        reasoning_levels=["Low", "Medium (default)", "High"],
    ),
    Model(
        id="gpt-5",
        name="GPT-5",
        provider="codex",
        description="Broad world knowledge with strong general reasoning",
        reasoning_levels=["Minimal", "Low", "Medium (default)", "High"],
    ),
]

GEMINI_MODELS = [
    Model(
        id="gemini-2-5-pro",
        name="Gemini 2.5 Pro",
        provider="gemini",
        description="State-of-the-art reasoning model with 1M token context",
    ),
    Model(
        id="gemini-2-5-flash",
        name="Gemini 2.5 Flash",
        provider="gemini",
        description="Best price-performance with 1M token context",
    ),
]

ALL_MODELS = CLAUDE_MODELS + CODEX_MODELS + GEMINI_MODELS


def get_models_for_provider(provider: str) -> list[Model]:
    """Get available models for a provider.

    Args:
        provider: Provider name (claude, codex, or gemini)

    Returns:
        List of Model objects for the provider
    """
    provider_lower = provider.lower()
    if provider_lower == "claude":
        return CLAUDE_MODELS
    elif provider_lower == "codex":
        return CODEX_MODELS
    elif provider_lower == "gemini":
        return GEMINI_MODELS
    else:
        raise ValueError(f"Unknown provider: {provider}")
