from typer.testing import CliRunner

from space.cli import app

runner = CliRunner()


def test_canon_path_command(mocker, tmp_path):
    # Mock canon_path to return a temporary path
    mocker.patch("space.canon.cli.canon_path", return_value=tmp_path / "my_canon_root")

    result = runner.invoke(app, ["canon", "path"])

    assert result.exit_code == 0
    assert f"Canon path: {tmp_path / 'my_canon_root'}" in result.stdout


def test_canon_list_command(mocker, tmp_path):
    # Create a temporary canon directory and mock files
    canon_dir = tmp_path / "my_canon"
    canon_dir.mkdir()
    (canon_dir / "doc1.md").write_text("Content 1")
    (canon_dir / "subdir").mkdir()
    (canon_dir / "subdir" / "doc2.md").write_text("Content 2")

    # Mock canon_path to return the temporary canon directory
    mocker.patch("space.canon.cli.canon_path", return_value=canon_dir)

    result = runner.invoke(app, ["canon", "list"])

    assert result.exit_code == 0
    assert f"Markdown documents in {canon_dir}:" in result.stdout
    assert "  - doc1.md" in result.stdout
    assert "  - subdir/doc2.md" in result.stdout


def test_canon_read_command(mocker, tmp_path):
    # Create a temporary canon directory and a mock file
    canon_dir = tmp_path / "my_canon"
    canon_dir.mkdir()
    (canon_dir / "test_doc.md").write_text("This is the content of the test document.")

    # Mock canon_path to return the temporary canon directory
    mocker.patch("space.canon.cli.canon_path", return_value=canon_dir)

    result = runner.invoke(app, ["canon", "read", "test_doc.md"])

    assert result.exit_code == 0
    assert "This is the content of the test document." in result.stdout


def test_canon_read_command_not_found(mocker, tmp_path):
    # Create a temporary canon directory
    canon_dir = tmp_path / "my_canon"
    canon_dir.mkdir()

    # Mock canon_path to return the temporary canon directory
    mocker.patch("space.canon.cli.canon_path", return_value=canon_dir)

    result = runner.invoke(app, ["canon", "read", "nonexistent_doc.md"])

    assert result.exit_code == 0
    assert "Document not found: nonexistent_doc.md" in result.stdout
