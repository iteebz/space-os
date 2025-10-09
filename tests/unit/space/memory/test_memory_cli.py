from typer.testing import CliRunner

from space.memory.cli import app

runner = CliRunner()


def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_memory_list_no_bridge_context(tmp_path, monkeypatch):
    monkeypatch.setenv("SPACE_HOME", str(tmp_path))
    
    from space.memory import db
    
    identity = "test-agent"
    db.add_entry(identity, "test-topic", "test message")
    
    result = runner.invoke(app, ["list", "--as", identity])
    assert result.exit_code == 0
    assert "test message" in result.stdout
    assert "BRIDGE INBOX" not in result.stdout
