from typer.testing import CliRunner

from space.memory.cli import app

runner = CliRunner()


def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_memory_list_no_bridge_context(test_space):
    from space.memory import db
    from space.spawn import registry

    identity = "test-agent"
    registry.init_db()
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "test-topic", "test message")

    result = runner.invoke(app, ["list", "--as", identity])
    assert result.exit_code == 0
    assert "test message" in result.stdout
    assert "BRIDGE INBOX" not in result.stdout


def test_memory_add(test_space):
    from space.spawn import registry

    registry.init_db()
    identity = "test-bot"
    registry.ensure_agent(identity)

    result = runner.invoke(app, ["add", "--as", identity, "--topic", "core", "fundamental truth"])
    assert result.exit_code == 0
    assert "Added memory" in result.stdout

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "core"])
    assert result.exit_code == 0
    assert "fundamental truth" in result.stdout


def test_memory_search(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "searcher"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "tech", "python is elegant")
    db.add_entry(agent_id, "tech", "rust is fast")
    db.add_entry(agent_id, "life", "coffee is essential")

    result = runner.invoke(app, ["search", "--as", identity, "elegant"])
    assert result.exit_code == 0
    assert "python is elegant" in result.stdout
    assert "rust is fast" not in result.stdout


def test_memory_archive_restore(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "archiver"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "temp", "ephemeral thought")

    entries = db.get_entries(identity, topic="temp")
    entry_id = entries[0].uuid

    result = runner.invoke(app, ["archive", entry_id])
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "temp"])
    assert "ephemeral thought" not in result.stdout

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "temp", "--archived"])
    assert "ephemeral thought" in result.stdout

    result = runner.invoke(app, ["archive", "--restore", entry_id])
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "temp"])
    assert "ephemeral thought" in result.stdout


def test_memory_delete(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "deleter"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "mistake", "wrong info")

    entries = db.get_entries(identity, topic="mistake")
    entry_id = entries[0].uuid

    result = runner.invoke(app, ["delete", entry_id], input="y\n")
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "mistake"])
    assert "wrong info" not in result.stdout


def test_memory_core_marking(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "philosopher"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "principle", "simplicity > complexity")

    entries = db.get_entries(identity, topic="principle")
    entry_id = entries[0].uuid

    result = runner.invoke(app, ["core", entry_id])
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "principle"])
    assert "CORE" in result.stdout or "★" in result.stdout

    result = runner.invoke(app, ["core", "--unmark", entry_id])
    assert result.exit_code == 0
