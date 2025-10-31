import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from space.os.canon.cli import app

runner = CliRunner()


def test_canon_tree_command():
    """Canon tree command shows hierarchy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "INDEX.md").write_text("# Index")
        (canon_root / "research").mkdir()
        (canon_root / "research" / "safety.md").write_text("# Safety")

        with patch("space.os.canon.api.entries.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["tree"])

        assert result.exit_code == 0
        assert "INDEX" in result.stdout or "research" in result.stdout


def test_canon_inspect_command():
    """Canon inspect command reads document."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        content = "# Test Document\nContent here."
        (canon_root / "test.md").write_text(content)

        with patch("space.os.canon.api.entries.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["inspect", "test"])

        assert result.exit_code == 0
        assert "# Test Document" in result.stdout
        assert "Content here." in result.stdout


def test_canon_inspect_nested():
    """Canon inspect handles nested paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "research").mkdir()
        content = "# Nested"
        (canon_root / "research" / "nested.md").write_text(content)

        with patch("space.os.canon.api.entries.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["inspect", "research/nested"])

        assert result.exit_code == 0
        assert "# Nested" in result.stdout


def test_canon_inspect_missing():
    """Canon inspect handles missing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "exists.md").write_text("# Exists")

        with patch("space.os.canon.api.entries.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["inspect", "missing"])

        assert result.exit_code == 0
        assert "Not found" in result.stdout
