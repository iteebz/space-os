
import pytest
from space.context import context
from space.context import db as context_db
from space.context.models import Knowledge, Memory


@pytest.fixture(autouse=True)
def setup_context_db(tmp_path):
    """Set up a temporary database for context module tests."""
    temp_db_path = tmp_path / "test_context.db"
    context_db.set_context_db_path(temp_db_path)
    context_db.ensure()
    yield
    # Teardown is implicit as tmp_path is cleaned up by pytest


def test_memory_memorize_and_get():
    identity = "test_agent"
    topic = "test_topic"
    message = "This is a test message."

    context.memory.memorize(identity, topic, message)

    entries = context.memory.get(identity, topic)
    assert len(entries) == 1
    assert isinstance(entries[0], Memory)
    assert entries[0].identity == identity
    assert entries[0].topic == topic
    assert entries[0].message == message


def test_knowledge_know_and_query_by_domain():
    contributor = "test_contributor"
    domain = "test_domain"
    content = "This is a piece of knowledge."

    context.knowledge.know(domain, contributor, content)

    entries = context.knowledge.query_by_domain(domain)
    assert len(entries) == 1
    assert isinstance(entries[0], Knowledge)
    assert entries[0].domain == domain
    assert entries[0].contributor == contributor
    assert entries[0].content == content


def test_memory_get_all_topics():
    identity = "test_agent_2"
    context.memory.memorize(identity, "topic_a", "message_a")
    context.memory.memorize(identity, "topic_b", "message_b")

    entries = context.memory.get(identity)
    assert len(entries) == 2
    topics = {e.topic for e in entries}
    assert "topic_a" in topics
    assert "topic_b" in topics


def test_memory_edit_entry():
    identity = "test_agent_3"
    topic = "edit_topic"
    message = "original message"
    context.memory.memorize(identity, topic, message)
    original_entry = context.memory.get(identity, topic)[0]

    new_message = "updated message"
    context.memory.edit(original_entry.uuid, new_message)

    updated_entry = context.memory.get(identity, topic)[0]
    assert updated_entry.message == new_message


def test_memory_delete_entry():
    identity = "test_agent_4"
    topic = "delete_topic"
    message = "message to delete"
    context.memory.memorize(identity, topic, message)
    entry_to_delete = context.memory.get(identity, topic)[0]

    context.memory.delete(entry_to_delete.uuid)
    entries = context.memory.get(identity, topic)
    assert len(entries) == 0


def test_memory_clear_entries():
    identity = "test_agent_5"
    context.memory.memorize(identity, "topic_x", "message_x")
    context.memory.memorize(identity, "topic_y", "message_y")

    context.memory.clear(identity, "topic_x")
    entries_x = context.memory.get(identity, "topic_x")
    assert len(entries_x) == 0
    entries_y = context.memory.get(identity, "topic_y")
    assert len(entries_y) == 1

    context.memory.clear(identity)
    all_entries = context.memory.get(identity)
    assert len(all_entries) == 0


def test_knowledge_query_by_contributor():
    contributor = "test_contributor_2"
    domain_a = "domain_a"
    domain_b = "domain_b"
    context.knowledge.know(domain_a, contributor, "content_a")
    context.knowledge.know(domain_b, contributor, "content_b")

    entries = context.knowledge.query_by_contributor(contributor)
    assert len(entries) == 2
    domains = {e.domain for e in entries}
    assert domain_a in domains
    assert domain_b in domains


def test_knowledge_list_all():
    context.knowledge.know("domain_list_all_1", "contrib_list_all_1", "content_list_all_1")
    context.knowledge.know("domain_list_all_2", "contrib_list_all_2", "content_list_all_2")

    entries = context.knowledge.list_all()
    assert (
        len(entries) >= 2
    )  # May include entries from other tests, but should have at least these two


def test_knowledge_get_by_id():
    contributor = "test_contributor_3"
    domain = "test_domain_3"
    content = "unique content"
    entry_id = context.knowledge.know(domain, contributor, content)

    retrieved_entry = context.knowledge.get_by_id(entry_id)
    assert retrieved_entry is not None
    assert retrieved_entry.id == entry_id
    assert retrieved_entry.content == content

    non_existent_entry = context.knowledge.get_by_id("non_existent_id")
    assert non_existent_entry is None
