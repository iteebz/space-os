from space.os import events


def test_emit_event(test_space):
    events.emit(
        "test_source",
        "test_type",
        agent_id="test_agent",
        data="test_data",
    )

    results = events.query()
    assert len(results) > 0
    result = results[-1]
    assert result.source == "test_source"
    assert result.event_type == "test_type"
    assert result.agent_id == "test_agent"
    assert result.data == "test_data"


def test_query_events(test_space):
    events.emit("test_src", "test_type", agent_id="agent1", data="data1")
    events.emit("other_src", "other_type", agent_id="agent2", data="data2")

    results = events.query(source="test_src")
    assert len(results) >= 1
    assert any(r.source == "test_src" for r in results)
