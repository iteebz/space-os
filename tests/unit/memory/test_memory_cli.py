from typer.testing import CliRunner

from space.memory.app import app

runner = CliRunner()


def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.stdout


def test_memory_default_to_list_and_sort_core(test_space):
    from space.memory import db
    from space.spawn import registry

    identity = "test-agent-default-list"
    registry.init_db()
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "topic-b", "message B")
    db.add_entry(agent_id, "topic-a", "message A")
    core_entry_id = db.add_entry(agent_id, "topic-c", "message C (core)")

    db.mark_core(core_entry_id[-8:], core=True)
    archived_entry_id = db.add_entry(agent_id, "topic-d", "message D (archived)")
    db.archive_entry(archived_entry_id)

    # Test default behavior (should list, not show archived, core at top)
    result = runner.invoke(app, ["--as", identity])
    assert result.exit_code == 0
    output_lines = result.stdout.strip().split("\n")

    # Verify core memory is at the top (after topic header)
    assert "# topic-c" in output_lines
    assert "message C (core) ★" in result.stdout
    assert output_lines[output_lines.index("# topic-c") + 1].endswith("message C (core) ★")

    # Verify other messages are present and archived is not
    assert "message A" in result.stdout
    assert "message B" in result.stdout
    assert "message D (archived)" not in result.stdout

    # Test explicit list command (should behave the same)
    result_explicit_list = runner.invoke(app, ["list", "--as", identity])
    assert result_explicit_list.exit_code == 0


def test_memory_list_no_bridge(test_space):
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


def test_memory_archive_and_restore(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "archiver"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "temp", "ephemeral thought")

    entries = db.get_memories(identity, topic="temp")
    entry_id = entries[0].memory_id

    result = runner.invoke(app, ["archive", entry_id])
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "temp"])
    assert "ephemeral thought" not in result.stdout


def test_memory_delete(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "deleter"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "mistake", "wrong info")

    entries = db.get_memories(identity, topic="mistake")
    entry_id = entries[0].memory_id

    result = runner.invoke(app, ["delete", entry_id], input="y\n")
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "mistake"])
    assert "wrong info" not in result.stdout


def test_memory_core_mark(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "philosopher"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "principle", "simplicity > complexity")

    entries = db.get_memories(identity, topic="principle")
    entry_id = entries[0].memory_id

    result = runner.invoke(app, ["core", entry_id])
    assert result.exit_code == 0

    result = runner.invoke(app, ["list", "--as", identity, "--topic", "principle"])
    assert "simplicity > complexity ★" in result.stdout

    result = runner.invoke(app, ["core", "--unmark", entry_id])
    assert result.exit_code == 0
