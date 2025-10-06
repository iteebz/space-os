import pytest
from space.apps.knowledge.api import write_knowledge, query_knowledge
from space.apps.knowledge.db import set_knowledge_db_path

@pytest.fixture(autouse=True)
def override_db_path(tmp_path):
    """Fixture to override the database path to a temporary directory."""
    db_path = tmp_path / "knowledge.db"
    set_knowledge_db_path(db_path)

def test_write_and_query_knowledge():
    """Test writing and querying a single knowledge entry."""
    entry_id = write_knowledge(
        domain="test_domain",
        contributor="test_contributor",
        content="test_content",
    )
    assert isinstance(entry_id, str)

    entries = query_knowledge(entry_id=entry_id)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == entry_id
    assert entry.domain == "test_domain"
    assert entry.contributor == "test_contributor"
    assert entry.content == "test_content"

def test_query_by_domain():
    """Test querying knowledge entries by domain."""
    write_knowledge("domain1", "contrib1", "content1")
    write_knowledge("domain2", "contrib2", "content2")
    write_knowledge("domain1", "contrib3", "content3")

    entries = query_knowledge(domain="domain1")
    assert len(entries) == 2
    assert all(entry.domain == "domain1" for entry in entries)

def test_query_by_contributor():
    """Test querying knowledge entries by contributor."""
    write_knowledge("domain1", "contrib1", "content1")
    write_knowledge("domain2", "contrib2", "content2")
    write_knowledge("domain3", "contrib1", "content3")

    entries = query_knowledge(contributor="contrib1")
    assert len(entries) == 2
    assert all(entry.contributor == "contrib1" for entry in entries)

def test_query_all():
    """Test querying all knowledge entries."""
    write_knowledge("domain1", "contrib1", "content1")
    write_knowledge("domain2", "contrib2", "content2")

    entries = query_knowledge()
    assert len(entries) == 2

def test_query_non_existent():
    """Test querying for a non-existent entry."""
    entries = query_knowledge(entry_id="non_existent_id")
    assert len(entries) == 0
