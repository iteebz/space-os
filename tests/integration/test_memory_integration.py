from space.core import memory, spawn


def test_memory_replace_single(test_space, default_agents):
    identity = default_agents["zealot"]
    agent_id = spawn.get_agent(identity).agent_id
    memory.add_entry(agent_id, "insight", "initial thought")

    entries = memory.list_entries(identity, topic="insight")
    old_id = entries[0].memory_id

    new_uuid = memory.replace_entry(
        [old_id], agent_id, "insight", "refined thought", "improved clarity"
    )
    assert new_uuid is not None

    active = memory.list_entries(identity, show_all=False)
    active_insights = [e for e in active if e.topic == "insight"]
    assert len(active_insights) == 1
    assert active_insights[0].message == "refined thought"

    archived_memories = memory.list_entries(identity, show_all=True)
    archived_entries = [e for e in archived_memories if e.archived_at is not None]
    assert len(archived_entries) == 1
    assert archived_entries[0].message == "initial thought"


def test_replace_merge(test_space, default_agents):
    identity = default_agents["sentinel"]
    agent_id = spawn.get_agent(identity).agent_id
    memory.add_entry(agent_id, "idea", "thought one")
    memory.add_entry(agent_id, "idea", "thought two")
    memory.add_entry(agent_id, "idea", "thought three")

    entries = memory.list_entries(identity, topic="idea")
    ids = [e.memory_id for e in entries]

    new_uuid = memory.replace_entry(
        ids, agent_id, "idea", "unified insight", "merged redundant thoughts"
    )
    assert new_uuid is not None
    active_memories = memory.list_entries(identity, show_all=False)
    active_ideas = [e for e in active_memories if e.topic == "idea"]
    assert len(active_ideas) == 1
    assert active_ideas[0].message == "unified insight"

    archived = memory.list_entries(identity, show_all=True)
    archived_entries = [e for e in archived if e.archived_at is not None]
    assert len(archived_entries) == 3


def test_memory_chain_query(test_space, default_agents):
    identity = default_agents["crucible"]
    agent_id = spawn.get_agent(identity).agent_id
    memory.add_entry(agent_id, "evolution", "version 1")

    memories = memory.list_entries(identity, topic="evolution")
    v1_id = memories[0].memory_id
    v2_id = memory.replace_entry([v1_id], agent_id, "evolution", "version 2", "iteration")

    chain = memory.get_chain(v2_id)
    assert chain["start_entry"] is not None
    assert len(chain["predecessors"]) == 1
    assert chain["predecessors"][0].message == "version 1"
    assert chain["start_entry"].message == "version 2"
    assert chain["start_entry"].synthesis_note == "iteration"


def test_memory_lineage_upward_traversal(test_space, default_agents):
    identity = default_agents["zealot"]
    agent_id = spawn.get_agent(identity).agent_id

    v1_id = memory.add_entry(agent_id, "thought", "version 1")
    v2_id = memory.replace_entry([v1_id], agent_id, "thought", "version 2")
    v3_id = memory.replace_entry([v2_id], agent_id, "thought", "version 3")

    chain = memory.get_chain(v3_id)
    assert chain["start_entry"].message == "version 3"
    assert len(chain["predecessors"]) == 2
    preds = {p.message for p in chain["predecessors"]}
    assert "version 1" in preds
    assert "version 2" in preds


def test_lineage_downward(test_space, default_agents):
    identity = default_agents["sentinel"]
    agent_id = spawn.get_agent(identity).agent_id

    v1_id = memory.add_entry(agent_id, "idea", "original")
    memory.replace_entry([v1_id], agent_id, "idea", "evolved")

    chain = memory.get_chain(v1_id)
    assert chain["start_entry"].message == "original"
    assert len(chain["successors"]) == 1
    assert chain["successors"][0].message == "evolved"


def test_lineage_merge(test_space, default_agents):
    identity = default_agents["crucible"]
    agent_id = spawn.get_agent(identity).agent_id

    id_a = memory.add_entry(agent_id, "notes", "idea A")
    id_b = memory.add_entry(agent_id, "notes", "idea B")
    id_c = memory.add_entry(agent_id, "notes", "idea C")
    merged_id = memory.replace_entry(
        [id_a, id_b, id_c], agent_id, "notes", "unified synthesis", "merged three threads"
    )

    chain = memory.get_chain(merged_id)
    assert chain["start_entry"].message == "unified synthesis"
    assert len(chain["predecessors"]) == 3
    pred_msgs = {p.message for p in chain["predecessors"]}
    assert pred_msgs == {"idea A", "idea B", "idea C"}

    chain_a = memory.get_chain(id_a)
    assert len(chain_a["successors"]) == 1
    assert chain_a["successors"][0].message == "unified synthesis"


def test_lineage_bidirectional(test_space, default_agents):
    identity = default_agents["zealot"]
    agent_id = spawn.get_agent(identity).agent_id

    v1_id = memory.add_entry(agent_id, "stream", "gen1")
    v2_id = memory.replace_entry([v1_id], agent_id, "stream", "gen2")
    v3_id = memory.replace_entry([v2_id], agent_id, "stream", "gen3")

    chain_v1 = memory.get_chain(v1_id)
    assert len(chain_v1["predecessors"]) == 0
    assert len(chain_v1["successors"]) == 2

    chain_v2 = memory.get_chain(v2_id)
    assert len(chain_v2["predecessors"]) == 1
    assert len(chain_v2["successors"]) == 1

    chain_v3 = memory.get_chain(v3_id)
    assert len(chain_v3["predecessors"]) == 2
    assert len(chain_v3["successors"]) == 0
