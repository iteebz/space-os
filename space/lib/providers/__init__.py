"""Unified provider implementations for Claude, Codex, Gemini.

Providers implement the Provider protocol (chat discovery, message parsing, spawning).
"""

from .claude import Claude
from .codex import Codex
from .gemini import Gemini

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
        {"id": "gpt-5-codex", "name": "GPT-5 Codex", "description": "Optimized for agentic coding"},
        {
            "id": "gpt-5",
            "name": "GPT-5",
            "description": "Broad world knowledge with strong reasoning",
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

__all__ = ["Claude", "Codex", "Gemini", "MODELS"]
