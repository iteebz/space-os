import tempfile
from pathlib import Path

from space.apps.context.lib import canon


def test_canon_search_finds_matching_documents():
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "doc1.md").write_text("This is a test document about apples.")
        (canon_root / "subdir").mkdir(parents=True, exist_ok=True)
        (canon_root / "subdir" / "doc2.md").write_text("Another document mentioning oranges.")
        (canon_root / "doc3.md").write_text("No match here.")

        # Mock canon_path to return our temporary directory
        original_canon_path = canon.canon_path
        canon.canon_path = lambda: canon_root

        try:
            results = canon.search("apples")
            assert len(results) == 1
            assert results[0]["source"] == "canon"
            assert results[0]["path"] == "doc1.md"
            assert "apples" in results[0]["content"].lower()
            assert results[0]["reference"] == "canon:doc1.md"

            results = canon.search("oranges")
            assert len(results) == 1
            assert results[0]["source"] == "canon"
            assert results[0]["path"] == str(Path("subdir") / "doc2.md")
            assert "oranges" in results[0]["content"].lower()
            assert results[0]["reference"] == f"canon:{Path('subdir') / 'doc2.md'}"

            results = canon.search("nomatch")
            assert len(results) == 0
        finally:
            canon.canon_path = original_canon_path


def test_canon_search_no_canon_root():
    original_canon_path = canon.canon_path
    canon.canon_path = lambda: Path("/nonexistent/path")

    try:
        results = canon.search("test")
        assert len(results) == 0
    finally:
        canon.canon_path = original_canon_path


def test_canon_search_empty_query():
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "doc1.md").write_text("This is a test document.")

        original_canon_path = canon.canon_path
        canon.canon_path = lambda: canon_root

        try:
            results = canon.search("")
            assert len(results) == 0  # Empty query should not match everything
        finally:
            canon.canon_path = original_canon_path
