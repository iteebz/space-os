"""Tests for constitution file management."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from space.lib.constitution import (
    PROVIDER_MAP,
    read_constitution,
    swap_constitution,
    write_constitution,
)


@pytest.fixture
def temp_home():
    """Fixture providing a temporary home directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_write_constitution_claude(temp_home):
    """Write constitution creates correct path for claude provider."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        content = "# Zealot Constitution\nYou are zealous."
        result = write_constitution("claude", content)

        assert result == temp_home / ".claude" / "CLAUDE.md"
        assert result.exists()
        assert result.read_text() == content


def test_write_constitution_gemini(temp_home):
    """Write constitution creates correct path for gemini provider."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        content = "# Gemini Constitution"
        result = write_constitution("gemini", content)

        assert result == temp_home / ".gemini" / "GEMINI.md"
        assert result.exists()
        assert result.read_text() == content


def test_write_constitution_codex(temp_home):
    """Write constitution creates correct path for codex provider."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        content = "# Codex Constitution"
        result = write_constitution("codex", content)

        assert result == temp_home / ".codex" / "AGENTS.md"
        assert result.exists()
        assert result.read_text() == content


def test_write_constitution_invalid_provider():
    """Write constitution raises ValueError for unknown provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        write_constitution("unknown", "content")


def test_write_constitution_creates_parent_dirs(temp_home):
    """Write constitution creates parent directories."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        content = "test"
        write_constitution("claude", content)

        assert (temp_home / ".claude").exists()
        assert (temp_home / ".claude" / "CLAUDE.md").exists()


def test_read_constitution_claude(temp_home):
    """Read constitution retrieves correct file for claude."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        content = "# Zealot"
        write_constitution("claude", content)

        result = read_constitution("claude")
        assert result == content


def test_read_constitution_not_exists(temp_home):
    """Read constitution returns None if file doesn't exist."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        result = read_constitution("claude")
        assert result is None


def test_read_constitution_invalid_provider():
    """Read constitution raises ValueError for unknown provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        read_constitution("unknown")


def test_swap_constitution_stores_original(temp_home):
    """Swap constitution returns original content."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        original = "# Original"
        write_constitution("claude", original)

        new_content = "# New"
        returned = swap_constitution("claude", new_content)

        assert returned == original
        assert read_constitution("claude") == new_content


def test_swap_constitution_no_original(temp_home):
    """Swap constitution returns empty string if no original exists."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        new_content = "# New"
        returned = swap_constitution("claude", new_content)

        assert returned == ""
        assert read_constitution("claude") == new_content


def test_swap_constitution_round_trip(temp_home):
    """Swap constitution enables restore pattern."""
    with patch("space.lib.constitution.Path.home", return_value=temp_home):
        original = "# Zealot"
        write_constitution("claude", original)

        ephemeral = "# Pepper"
        saved = swap_constitution("claude", ephemeral)

        assert read_constitution("claude") == ephemeral

        swap_constitution("claude", saved)
        assert read_constitution("claude") == original


def test_provider_map_completeness():
    """PROVIDER_MAP contains all expected providers."""
    expected = {"claude", "gemini", "codex"}
    assert set(PROVIDER_MAP.keys()) == expected


def test_provider_map_values():
    """PROVIDER_MAP values are correct tuples."""
    assert PROVIDER_MAP["claude"] == ("CLAUDE.md", ".claude")
    assert PROVIDER_MAP["gemini"] == ("GEMINI.md", ".gemini")
    assert PROVIDER_MAP["codex"] == ("AGENTS.md", ".codex")
