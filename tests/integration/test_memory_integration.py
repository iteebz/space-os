from typer.testing import CliRunner

from space.memory.cli import app

runner = CliRunner()


def test_memory_shows_readme():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "memory" in result.stdout.lower()


def test_memory_add_requires_identity():
    result = runner.invoke(app, ["add", "test content"])
    assert result.exit_code != 0


def test_memory_add_with_identity():
    result = runner.invoke(app, ["add", "test memory", "--as", "test-agent", "--topic", "testing"])
    assert result.exit_code == 0
    assert "added" in result.stdout.lower() or "memory" in result.stdout.lower()


def test_memory_replace_single(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "replacer"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "insight", "initial thought")

    entries = db.get_entries(identity, topic="insight")
    old_id = entries[0].uuid

    new_uuid = db.replace_entry([old_id], agent_id, "insight", "refined thought", "improved clarity")
    assert new_uuid is not None

    active = db.get_entries(identity, include_archived=False)
    active_insights = [e for e in active if e.topic == "insight"]
    assert len(active_insights) == 1
    assert active_insights[0].message == "refined thought"

    archived = db.get_entries(identity, include_archived=True)
    archived_entries = [e for e in archived if e.archived_at is not None]
    assert len(archived_entries) == 1
    assert archived_entries[0].message == "initial thought"


def test_memory_replace_multi_merge(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "merger"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "idea", "thought one")
    db.add_entry(agent_id, "idea", "thought two")
    db.add_entry(agent_id, "idea", "thought three")

    entries = db.get_entries(identity, topic="idea")
    ids = [e.uuid for e in entries]

    new_uuid = db.replace_entry(ids, agent_id, "idea", "unified insight", "merged redundant thoughts")
    assert new_uuid is not None

    active = db.get_entries(identity, include_archived=False)
    active_ideas = [e for e in active if e.topic == "idea"]
    assert len(active_ideas) == 1
    assert active_ideas[0].message == "unified insight"

    archived = db.get_entries(identity, include_archived=True)
    archived_entries = [e for e in archived if e.archived_at is not None]
    assert len(archived_entries) == 3


def test_memory_chain_query(test_space):
    from space.memory import db
    from space.spawn import registry

    registry.init_db()
    identity = "tracer"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "evolution", "version 1")

    entries = db.get_entries(identity, topic="evolution")
    v1_id = entries[0].uuid

    v2_id = db.replace_entry([v1_id], agent_id, "evolution", "version 2", "iteration")

    chain = db.get_chain(v2_id)
    assert chain["current"] is not None
    assert len(chain["predecessors"]) == 1
    assert chain["predecessors"][0].message == "version 1"
    assert chain["current"].message == "version 2"
    assert chain["current"].synthesis_note == "iteration"
