def test_add_note_converts_identity_to_agent_id(test_space):
    """Regression test: add_note should convert identity name to agent_id."""
    from space.os.bridge import api, db
    from space.os.spawn import registry

    channel_id = api.create_channel("note-test-channel")
    identity = "test-agent"
    registry.ensure_agent(identity)

    api.add_note(channel_id, identity, "test note content")

    notes = db.get_notes(channel_id)
    assert len(notes) == 1
    assert notes[0].agent_id == registry.get_agent_id(identity), (
        "Note should store agent_id not identity name"
    )
    assert notes[0].content == "test note content"


def test_get_notes_returns_agent_id_not_name(test_space):
    """Regression test: get_notes should return agent_id UUIDs for lookups."""
    from space.os.bridge import api, db
    from space.os.spawn import registry

    channel_id = api.create_channel("note-uuid-test")
    identity = "note-agent"
    agent_id = registry.ensure_agent(identity)

    api.add_note(channel_id, identity, "note content")

    notes = db.get_notes(channel_id)
    assert len(notes) == 1

    assert hasattr(notes[0], "agent_id")
    assert notes[0].agent_id == agent_id
    assert isinstance(notes[0].agent_id, str)
    assert len(notes[0].agent_id) == 36, "agent_id should be UUID format"
