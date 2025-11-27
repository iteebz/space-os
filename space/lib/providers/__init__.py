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
            "description": "Fast, lightweight Claude for most tasks",
            "tags": ["default", "low-cost"],
        },
        {
            "id": "claude-sonnet-4-5",
            "name": "Claude Sonnet 4.5",
            "description": "Balanced Claude for agents and coding",
            "tags": ["general"],
        },
        {
            "id": "claude-opus-4-5",
            "name": "Claude Opus 4.5",
            "description": "Flagship Claude for complex, high-stakes reasoning",
            "tags": ["heavy"],
        },
    ],
    "codex": [
        {
            "id": "gpt-5.1-codex-low",
            "name": "GPT-5.1 Codex (Low)",
            "description": "Optimized for codex with lighter, cheaper reasoning",
            "tags": ["default-codex", "low"],
        },
        {
            "id": "gpt-5.1-codex-mini",
            "name": "GPT-5.1 Codex Mini",
            "description": "Cheaper, faster Codex; best for simple edits and scaffolding",
            "tags": ["mini", "low"],
        },
        {
            "id": "gpt-5.1-codex-medium",
            "name": "GPT-5.1 Codex (Medium)",
            "description": "Optimized for codex with balanced depth and speed",
            "tags": ["medium"],
        },
        {
            "id": "gpt-5.1-codex-high",
            "name": "GPT-5.1 Codex (High)",
            "description": "Optimized for codex with deep reasoning",
            "tags": ["high"],
        },
        {
            "id": "gpt-5.1-codex-max",
            "name": "GPT-5.1 Codex Max",
            "description": "Latest Codex-optimized flagship for deepest reasoning",
            "tags": ["max"],
        },
        {
            "id": "gpt-5.1-codex-mini-medium",
            "name": "GPT-5.1 Codex Mini (Medium)",
            "description": "Mini Codex with balanced reasoning depth",
            "tags": ["mini", "medium"],
        },
        {
            "id": "gpt-5.1-codex-mini-high",
            "name": "GPT-5.1 Codex Mini (High)",
            "description": "Mini Codex with higher reasoning depth",
            "tags": ["mini", "high"],
        },
        {
            "id": "gpt-5.1-low",
            "name": "GPT-5.1 (Low)",
            "description": "General reasoning with lower effort and cost",
            "tags": ["default-general", "low"],
        },
        {
            "id": "gpt-5.1-medium",
            "name": "GPT-5.1 (Medium)",
            "description": "General reasoning with balanced depth and speed",
            "tags": ["medium"],
        },
        {
            "id": "gpt-5.1-high",
            "name": "GPT-5.1 (High)",
            "description": "General reasoning with higher reasoning depth",
            "tags": ["high"],
        },
    ],
    "gemini": [
        {
            "id": "gemini-2-5-flash-lite",
            "name": "Gemini 2.5 Flash Lite",
            "description": "Fastest Gemini tier for simple or high-volume tasks",
            "tags": ["default", "lite"],
        },
        {
            "id": "gemini-2-5-flash",
            "name": "Gemini 2.5 Flash",
            "description": "Balanced speed and reasoning with 1M token context",
            "tags": ["balanced"],
        },
        {
            "id": "gemini-3-pro-preview",
            "name": "Gemini 3 Pro (preview)",
            "description": "Latest Pro-tier Gemini for complex reasoning and creativity",
            "tags": ["pro", "experimental"],
        },
        {
            "id": "gemini-2-5-pro",
            "name": "Gemini 2.5 Pro",
            "description": "Stable Pro model for deep reasoning with 1M token context",
            "tags": ["pro"],
        },
    ],
}

__all__ = ["Claude", "Codex", "Gemini", "MODELS", "PROVIDER_NAMES", "get_provider"]
