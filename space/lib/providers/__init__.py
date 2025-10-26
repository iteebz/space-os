"""Unified provider implementations for Claude, Codex, Gemini.

Providers implement the Provider protocol (chat discovery, message parsing, spawning).
"""

from .claude import Claude
from .codex import Codex
from .gemini import Gemini

claude = Claude()
codex = Codex()
gemini = Gemini()

__all__ = ["claude", "codex", "gemini", "Claude", "Codex", "Gemini"]
