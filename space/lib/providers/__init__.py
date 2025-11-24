"""Unified provider implementations for Claude, Codex, Gemini.

Providers implement the Provider protocol (chat discovery, message parsing, spawning).
"""

import sys

from .claude import Claude
from .codex import Codex
from .gemini import Gemini

PROVIDER_NAMES = ("claude", "codex", "gemini")


def get_provider(name: str):
    """Get provider class by name.

    Args:
        name: Provider name (claude, codex, gemini)

    Returns:
        Provider class

    Raises:
        ValueError: If provider not found
    """
    try:
        return getattr(sys.modules[__name__], name.capitalize())
    except AttributeError:
        raise ValueError(f"Unknown provider: {name}") from None


MODELS = {
    "claude": [
        {
            "id": "claude-sonnet-4-5",
            "name": "Claude Sonnet 4.5",
            "description": "Latest and most intelligent model, best for complex agents and coding tasks",
        },
        {
            "id": "claude-opus-4-1",
            "name": "Claude Opus 4.1",
            "description": "Maximum capability for complex development tasks",
        },
        {
            "id": "claude-haiku-4-5",
            "name": "Claude Haiku 4.5",
            "description": "Lightweight with 90% capability at 3x lower cost",
        },
    ],
    "codex": [
        {"id": "gpt-5.1-codex", "name": "GPT-5.1 Codex", "description": "Optimized for codex"},
        {
            "id": "gpt-5.1-codex-low",
            "name": "GPT-5.1 Codex (Low)",
            "description": "Optimized for codex, low reasoning effort",
        },
        {
            "id": "gpt-5.1-codex-medium",
            "name": "GPT-5.1 Codex (Medium)",
            "description": "Optimized for codex, medium reasoning effort",
        },
        {
            "id": "gpt-5.1-codex-high",
            "name": "GPT-5.1 Codex (High)",
            "description": "Optimized for codex, high reasoning effort",
        },
        {
            "id": "gpt-5.1-codex-mini",
            "name": "GPT-5.1 Codex Mini",
            "description": "Cheaper, faster, less capable",
        },
        {
            "id": "gpt-5.1-codex-mini-medium",
            "name": "GPT-5.1 Codex Mini (Medium)",
            "description": "Cheaper, faster, medium reasoning effort",
        },
        {
            "id": "gpt-5.1-codex-mini-high",
            "name": "GPT-5.1 Codex Mini (High)",
            "description": "Cheaper, faster, high reasoning effort",
        },
        {
            "id": "gpt-5.1",
            "name": "GPT-5.1",
            "description": "Broad world knowledge with strong reasoning",
        },
        {
            "id": "gpt-5.1-low",
            "name": "GPT-5.1 (Low)",
            "description": "General reasoning, low effort",
        },
        {
            "id": "gpt-5.1-medium",
            "name": "GPT-5.1 (Medium)",
            "description": "General reasoning, medium effort",
        },
        {
            "id": "gpt-5.1-high",
            "name": "GPT-5.1 (High)",
            "description": "General reasoning, high effort",
        },
    ],
    "gemini": [
        {
            "id": "gemini-2-5-pro",
            "name": "Gemini 2.5 Pro",
            "description": "State-of-the-art reasoning model with 1M token context",
        },
        {
            "id": "gemini-2-5-flash",
            "name": "Gemini 2.5 Flash",
            "description": "Best price-performance with 1M token context",
        },
    ],
}

__all__ = ["Claude", "Codex", "Gemini", "MODELS", "PROVIDER_NAMES", "get_provider"]
