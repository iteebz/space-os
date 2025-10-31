import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from space.os.canon.cli import app

runner = CliRunner()


def test_canon_shows_tree_when_no_args():
    """Canon shows directory tree when called with no arguments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "INDEX.md").write_text("# Index")
        (canon_root / "constitutions").mkdir()
        (canon_root / "constitutions" / "zealot.md").write_text("# Zealot")

        with patch("space.os.canon.cli.canon_path", return_value=canon_root):
            result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "INDEX.md" in result.stdout
        assert "constitutions" in result.stdout
        assert "Navigate with: space canon <path>" in result.stdout


def test_canon_reads_document():
    """Canon reads and displays document content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        content = "# Test Document\nThis is test content."
        (canon_root / "test.md").write_text(content)

        with patch("space.os.canon.cli.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["test.md"])

        assert result.exit_code == 0
        assert "# Test Document" in result.stdout
        assert "This is test content." in result.stdout


def test_canon_reads_nested_document():
    """Canon reads documents in subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "subdir").mkdir()
        content = "# Nested Document"
        (canon_root / "subdir" / "nested.md").write_text(content)

        with patch("space.os.canon.cli.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["subdir/nested.md"])

        assert result.exit_code == 0
        assert "# Nested Document" in result.stdout


def test_canon_handles_missing_document():
    """Canon handles missing documents gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canon_root = Path(tmpdir)
        (canon_root / "exists.md").write_text("# Exists")

        with patch("space.os.canon.cli.canon_path", return_value=canon_root):
            result = runner.invoke(app, ["missing.md"])

        assert result.exit_code == 1
        assert "Document not found" in result.stdout


def test_canon_handles_missing_canon_root():
    """Canon handles missing canon directory."""
    with patch("space.os.canon.cli.canon_path", return_value=Path("/nonexistent")):
        result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "Canon directory not found" in result.output
