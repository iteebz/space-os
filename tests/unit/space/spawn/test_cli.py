import json
from pathlib import Path

from typer.testing import CliRunner

from space.spawn import registry
from space.spawn.cli import app

runner = CliRunner()


def test_list_json_output(monkeypatch):
    with runner.isolated_filesystem() as temp_dir:
        monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
        registry.init_db()
        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)


def test_list_quiet_mode(monkeypatch):
    with runner.isolated_filesystem() as temp_dir:
        monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
        registry.init_db()
        result = runner.invoke(app, ["list", "--quiet"])
        assert result.exit_code == 0
        assert result.stdout == ""


def test_register_json_output(monkeypatch):
    with runner.isolated_filesystem() as temp_dir:
        monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
        registry.init_db()
        result = runner.invoke(app, ["register", "zealot", "test-agent", "test-topic", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["role"] == "zealot"
        assert data["agent_name"] == "test-agent"
        assert data["topic"] == "test-topic"


def test_register_quiet_mode(monkeypatch):
    with runner.isolated_filesystem() as temp_dir:
        monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
        registry.init_db()
        result = runner.invoke(
            app, ["register", "zealot", "test-agent-2", "test-topic-2", "--quiet"]
        )
        assert result.exit_code == 0
        assert result.stdout == ""


def test_unregister_json_output(monkeypatch):
    with runner.isolated_filesystem() as temp_dir:
        monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
        registry.init_db()
        runner.invoke(app, ["register", "zealot", "test-unreg", "test-topic"])
        result = runner.invoke(app, ["unregister", "zealot", "test-unreg", "test-topic", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["status"] == "success"


def test_unregister_not_found_json(monkeypatch):
    with runner.isolated_filesystem() as temp_dir:
        monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
        registry.init_db()
        result = runner.invoke(app, ["unregister", "zealot", "nonexistent", "topic", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["status"] == "error"
