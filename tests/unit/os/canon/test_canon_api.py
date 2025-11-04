"""Canon API tests."""

from pathlib import Path
from unittest.mock import patch

import pytest

from space.os.canon import api as canon_api


@pytest.fixture
def mock_canon_dir(tmp_path):
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    return canon_dir


def test_get_canon_entries_empty(mock_canon_dir):
    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.get_canon_entries()
        assert result == {}


def test_get_canon_entries_hierarchy(mock_canon_dir):
    (mock_canon_dir / "architecture").mkdir()
    (mock_canon_dir / "architecture" / "overview.md").write_text("# Overview")
    (mock_canon_dir / "architecture" / "caching.md").write_text("# Caching")
    (mock_canon_dir / "patterns.md").write_text("# Patterns")

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.get_canon_entries()
        assert "architecture" in result
        assert "overview" in result["architecture"]
        assert "caching" in result["architecture"]
        assert "patterns" in result


def test_read_canon_basic(mock_canon_dir):
    content = "# Architecture\n\nDetails here"
    (mock_canon_dir / "architecture.md").write_text(content)

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.read_canon("architecture")
        assert result is not None
        assert result.path == "architecture"
        assert result.content == content


def test_read_canon_with_extension(mock_canon_dir):
    content = "test content"
    (mock_canon_dir / "test.md").write_text(content)

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.read_canon("test.md")
        assert result is not None
        assert result.content == content


def test_read_canon_nested(mock_canon_dir):
    (mock_canon_dir / "docs").mkdir()
    content = "nested content"
    (mock_canon_dir / "docs" / "nested.md").write_text(content)

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.read_canon("docs/nested")
        assert result is not None
        assert result.path == "docs/nested"
        assert result.content == content


def test_read_canon_missing():
    mock_dir = Path("/nonexistent")
    with patch("space.os.canon.api.canon_path", return_value=mock_dir):
        result = canon_api.read_canon("missing")
        assert result is None


def test_canon_exists(mock_canon_dir):
    (mock_canon_dir / "exists.md").write_text("content")

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        assert canon_api.canon_exists("exists") is True
        assert canon_api.canon_exists("exists.md") is True
        assert canon_api.canon_exists("missing") is False


def test_search_by_path(mock_canon_dir):
    (mock_canon_dir / "architecture.md").write_text("unrelated content")
    (mock_canon_dir / "caching.md").write_text("unrelated content")

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        results = canon_api.search("arch")
        assert len(results) >= 1
        assert any(r["path"] == "architecture.md" for r in results)


def test_search_by_content(mock_canon_dir):
    (mock_canon_dir / "doc.md").write_text("This mentions elasticsearch specifically")

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        results = canon_api.search("elasticsearch")
        assert len(results) >= 1
        assert results[0]["path"] == "doc.md"


def test_search_prioritizes_path_matches(mock_canon_dir):
    (mock_canon_dir / "cache.md").write_text("content about queries")
    (mock_canon_dir / "queries.md").write_text("mentions cache here")

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        results = canon_api.search("cache")
        assert len(results) >= 2
        assert results[0]["path"] == "cache.md"


def test_search_empty_query(mock_canon_dir):
    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        results = canon_api.search("")
        assert results == []


def test_search_truncates_content(mock_canon_dir):
    long_content = "x" * 1000
    (mock_canon_dir / "large.md").write_text(long_content)

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        results = canon_api.search("x", max_content_length=100)
        assert len(results) == 1
        assert len(results[0]["content"]) == 101
        assert results[0]["content"].endswith("…")


def test_stats_empty(mock_canon_dir):
    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.stats()
        assert result["available"] is True
        assert result["total_files"] == 0
        assert result["total_size_bytes"] == 0


def test_stats_counts_files(mock_canon_dir):
    (mock_canon_dir / "doc1.md").write_text("content1")
    (mock_canon_dir / "doc2.md").write_text("content2")

    with patch("space.os.canon.api.canon_path", return_value=mock_canon_dir):
        result = canon_api.stats()
        assert result["available"] is True
        assert result["total_files"] == 2
        assert result["total_size_bytes"] > 0


def test_stats_missing_canon():
    mock_dir = Path("/nonexistent")
    with patch("space.os.canon.api.canon_path", return_value=mock_dir):
        result = canon_api.stats()
        assert result["available"] is False
        assert result["total_files"] == 0
