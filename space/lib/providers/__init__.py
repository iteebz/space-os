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
            "id": "claude-haiku-4-5",
            "name": "Claude Haiku 4.5",
            "description": "Fast, lightweight",
        },
        {
            "id": "claude-sonnet-4-5",
            "name": "Claude Sonnet 4.5",
            "description": "Balanced, general purpose",
        },
        {
            "id": "claude-opus-4-5",
            "name": "Claude Opus 4.5",
            "description": "Flagship, complex reasoning",
        },
    ],
    "codex": [
        {
            "id": "gpt-5.1",
            "name": "GPT-5.1",
            "description": "General reasoning",
        },
        {
            "id": "gpt-5.1-codex",
            "name": "GPT-5.1 Codex",
            "description": "Codex-optimized",
        },
        {
            "id": "gpt-5.1-codex-mini",
            "name": "GPT-5.1 Codex Mini",
            "description": "Cheap, fast",
        },
        {
            "id": "gpt-5.1-codex-max",
            "name": "GPT-5.1 Codex Max",
            "description": "Flagship",
        },
    ],
    "gemini": [
        {
            "id": "gemini-2-5-flash-lite",
            "name": "Gemini 2.5 Flash Lite",
            "description": "Fastest, simple tasks",
        },
        {
            "id": "gemini-2-5-flash",
            "name": "Gemini 2.5 Flash",
            "description": "Balanced, 1M context",
        },
        {
            "id": "gemini-2-5-pro",
            "name": "Gemini 2.5 Pro",
            "description": "Stable flagship",
        },
        {
            "id": "gemini-3-pro-preview",
            "name": "Gemini 3 Pro",
            "description": "Flagship (experimental)",
        },
    ],
}

__all__ = ["Claude", "Codex", "Gemini", "MODELS", "PROVIDER_NAMES", "get_provider"]
