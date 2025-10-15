from pathlib import Path
from unittest.mock import MagicMock

from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_context_displays_canon_docs(mocker, tmp_path):
    # Create a temporary canon directory and a mock canon file
    canon_dir = tmp_path / "my_canon"
    canon_dir.mkdir()
    mock_canon_file = canon_dir / "test_doc.md"
    mock_canon_file.write_text(
        "# Test Canon Document\nThis is some content about constitutional cognitive infrastructure."
    )

    # Mock canon_path to return the temporary canon directory
    mocker.patch("space.context.app.canon_path", return_value=canon_dir)

    # Mock Path.rglob to return the mock canon file
    mock_rglob_return = MagicMock()
    mock_rglob_return.__iter__.return_value = [mock_canon_file]
    mocker.patch.object(Path, "rglob", return_value=mock_rglob_return)

    # Mock db.collect_timeline and db.collect_current_state to return empty data
    mocker.patch("space.context.db.collect_timeline", return_value=[])
    mocker.patch(
        "space.context.db.collect_current_state",
        return_value={"memory": [], "knowledge": [], "bridge": []},
    )

    # Run the context command with a topic that exists in the mock canon file
    result = runner.invoke(app, ["context", "constitutional cognitive infrastructure"])

    # Assert that the output contains the canon document's content
    assert result.exit_code == 0
    assert "## CANON DOCS" in result.stdout
    assert "### test_doc.md" in result.stdout
    assert "constitutional cognitive infrastructure" in result.stdout


def test_context_no_canon_docs_found(mocker, tmp_path):
    # Create an empty temporary canon directory
    canon_dir = tmp_path / "empty_canon"
    canon_dir.mkdir()

    # Mock canon_path to return the empty temporary canon directory
    mocker.patch("space.context.app.canon_path", return_value=canon_dir)

    # Mock Path.rglob to return an empty iterator
    mock_rglob_return = MagicMock()
    mock_rglob_return.__iter__.return_value = []
    mocker.patch.object(Path, "rglob", return_value=mock_rglob_return)

    # Mock db.collect_timeline and db.collect_current_state to return empty data
    mocker.patch("space.context.db.collect_timeline", return_value=[])
    mocker.patch(
        "space.context.db.collect_current_state",
        return_value={"memory": [], "knowledge": [], "bridge": []},
    )

    # Run the context command with a topic
    result = runner.invoke(app, ["context", "nonexistent topic"])

    # Assert that canon docs section is not displayed
    assert result.exit_code == 0
    assert "## CANON DOCS" not in result.stdout
    assert "No context found for 'nonexistent topic'" in result.stdout
