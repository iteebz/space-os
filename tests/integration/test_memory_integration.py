from typer.testing import CliRunner

from space.os.memory.app import app

runner = CliRunner()


def test_memory_shows_readme():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "memory" in result.stdout.lower()


def test_add_requires_identity():
    result = runner.invoke(app, ["add", "test content"])
    assert result.exit_code != 0


def test_add_with_identity():
    result = runner.invoke(app, ["add", "test memory", "--as", "test-agent", "--topic", "testing"])
    assert result.exit_code == 0
    assert "added" in result.stdout.lower() or "memory" in result.stdout.lower()


def test_memory_replace_single(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "replacer"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "insight", "initial thought")

    entries = db.get_memories(identity, topic="insight")
    old_id = entries[0].memory_id

    new_uuid = db.replace_entry(
        [old_id], agent_id, "insight", "refined thought", "improved clarity"
    )
    assert new_uuid is not None

    active = db.get_memories(identity, include_archived=False)
    active_insights = [e for e in active if e.topic == "insight"]
    assert len(active_insights) == 1
    assert active_insights[0].message == "refined thought"

    archived_memories = db.get_memories(identity, include_archived=True)
    archived_entries = [e for e in archived_memories if e.archived_at is not None]
    assert len(archived_entries) == 1
    assert archived_entries[0].message == "initial thought"


def test_replace_merge(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "merger"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "idea", "thought one")
    db.add_entry(agent_id, "idea", "thought two")
    db.add_entry(agent_id, "idea", "thought three")

    entries = db.get_memories(identity, topic="idea")
    ids = [e.memory_id for e in entries]

    new_uuid = db.replace_entry(
        ids, agent_id, "idea", "unified insight", "merged redundant thoughts"
    )
    assert new_uuid is not None
    active_memories = db.get_memories(identity, include_archived=False)
    active_ideas = [e for e in active_memories if e.topic == "idea"]
    assert len(active_ideas) == 1
    assert active_ideas[0].message == "unified insight"

    archived = db.get_memories(identity, include_archived=True)
    archived_entries = [e for e in archived if e.archived_at is not None]
    assert len(archived_entries) == 3


def test_memory_chain_query(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "tracer"
    agent_id = registry.ensure_agent(identity)
    db.add_entry(agent_id, "evolution", "version 1")

    memories = db.get_memories(identity, topic="evolution")
    v1_id = memories[0].memory_id
    v2_id = db.replace_entry([v1_id], agent_id, "evolution", "version 2", "iteration")

    chain = db.get_chain(v2_id)
    chain = db.get_chain(v2_id)
    assert chain["start_entry"] is not None
    assert len(chain["predecessors"]) == 1
    assert chain["predecessors"][0].message == "version 1"
    assert chain["start_entry"].message == "version 2"
    assert chain["start_entry"].synthesis_note == "iteration"


def test_memory_lineage_upward_traversal(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "lineage"
    agent_id = registry.ensure_agent(identity)

    v1_id = db.add_entry(agent_id, "thought", "version 1")
    v2_id = db.replace_entry([v1_id], agent_id, "thought", "version 2")
    v3_id = db.replace_entry([v2_id], agent_id, "thought", "version 3")

    chain = db.get_chain(v3_id)
    assert chain["start_entry"].message == "version 3"
    assert len(chain["predecessors"]) == 2
    preds = {p.message for p in chain["predecessors"]}
    assert "version 1" in preds
    assert "version 2" in preds


def test_memory_lineage_downward_traversal(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "descend"
    agent_id = registry.ensure_agent(identity)

    v1_id = db.add_entry(agent_id, "idea", "original")
    db.replace_entry([v1_id], agent_id, "idea", "evolved")

    chain = db.get_chain(v1_id)
    assert chain["start_entry"].message == "original"
    assert len(chain["successors"]) == 1
    assert chain["successors"][0].message == "evolved"


def test_memory_lineage_merge_predecessors(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "merger"
    agent_id = registry.ensure_agent(identity)

    id_a = db.add_entry(agent_id, "notes", "idea A")
    id_b = db.add_entry(agent_id, "notes", "idea B")
    id_c = db.add_entry(agent_id, "notes", "idea C")
    merged_id = db.replace_entry(
        [id_a, id_b, id_c], agent_id, "notes", "unified synthesis", "merged three threads"
    )

    chain = db.get_chain(merged_id)
    assert chain["start_entry"].message == "unified synthesis"
    assert len(chain["predecessors"]) == 3
    pred_msgs = {p.message for p in chain["predecessors"]}
    assert pred_msgs == {"idea A", "idea B", "idea C"}

    chain_a = db.get_chain(id_a)
    assert len(chain_a["successors"]) == 1
    assert chain_a["successors"][0].message == "unified synthesis"


def test_memory_lineage_bidirectional_traversal(test_space):
    from space.os.memory import db
    from space.os.spawn import registry

    registry.init_db()
    identity = "bidir"
    agent_id = registry.ensure_agent(identity)

    v1_id = db.add_entry(agent_id, "stream", "gen1")
    v2_id = db.replace_entry([v1_id], agent_id, "stream", "gen2")
    v3_id = db.replace_entry([v2_id], agent_id, "stream", "gen3")

    chain_v1 = db.get_chain(v1_id)
    assert len(chain_v1["predecessors"]) == 0
    assert len(chain_v1["successors"]) == 2

    chain_v2 = db.get_chain(v2_id)
    assert len(chain_v2["predecessors"]) == 1
    assert len(chain_v2["successors"]) == 1

    chain_v3 = db.get_chain(v3_id)
    assert len(chain_v3["predecessors"]) == 2
    assert len(chain_v3["successors"]) == 0
