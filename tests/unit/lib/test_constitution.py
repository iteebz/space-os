"""Tests for constitution file management."""

import pytest

from space.os.spawn.api.constitute import PROVIDER_MAP




def test_provider_map_completeness():
    """PROVIDER_MAP contains all expected providers."""
    expected = {"claude", "gemini", "codex"}
    assert set(PROVIDER_MAP.keys()) == expected


def test_provider_map_values():
    """PROVIDER_MAP values are correct filenames."""
    assert PROVIDER_MAP["claude"] == "CLAUDE.md"
    assert PROVIDER_MAP["gemini"] == "GEMINI.md"
    assert PROVIDER_MAP["codex"] == "AGENTS.md"
