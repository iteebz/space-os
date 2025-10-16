from typer.testing import CliRunner

from space.app import app

runner = CliRunner()


def test_context_with_canon_docs(test_space, monkeypatch):
    monkeypatch.chdir(test_space)
    canon_dir = test_space / "canon"
    canon_dir.mkdir()
    (canon_dir / "infra.md").write_text("# Constitutional Infrastructure")
    
    result = runner.invoke(app, ["context", "infra"])
    
    assert result.exit_code == 0


def test_context_missing_topic(test_space, monkeypatch):
    monkeypatch.chdir(test_space)
    result = runner.invoke(app, ["context", "nonexistent-topic-xyz"])
    
    assert result.exit_code == 0
