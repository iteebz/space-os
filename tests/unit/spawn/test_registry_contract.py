import hashlib
import time

import pytest

from space.registry import registry
from space.spawn import config


@pytest.fixture
def setup_spawn_db(tmp_path, monkeypatch):
    # Use a temporary directory for the spawn.db
    spawn_dir = tmp_path / ".spawn"
    spawn_dir.mkdir()
    registry_db_path = spawn_dir / "spawn.db"

    monkeypatch.setattr(config, "spawn_dir", lambda: spawn_dir)
    monkeypatch.setattr(config, "registry_db", lambda: registry_db_path)

    registry.init_db()
    yield


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def test_registry_stores_multiple_constitution_versions(setup_spawn_db):
    sender_id = "test-agent"
    topic = "test-topic"
    role = "test-role"
    model = "test-model"

    # Version 1 of the constitution
    constitution_content_v1 = "This is the first version of the constitution."
    constitution_hash_v1 = hash_content(constitution_content_v1)

    # Add the first entry
    registry.register(
        role,
        sender_id,
        topic,
        identity_hash=constitution_hash_v1,
        identity=constitution_content_v1,
        model=model,
    )

    time.sleep(0.5)

    # Version 2 of the constitution
    constitution_content_v2 = "This is the second version of the constitution, with changes."
    constitution_hash_v2 = hash_content(constitution_content_v2)

    # Add the second entry (same sender_id, same topic, different hash/content)
    registry.register(
        role,
        sender_id,
        topic,
        identity_hash=constitution_hash_v2,
        identity=constitution_content_v2,
        model=model,
    )

    # Retrieve all entries for the sender_id and topic
    entries = registry.list_entries()
    filtered_entries = [e for e in entries if e.sender_id == sender_id and e.topic == topic]

    # Assert that both entries exist
    assert len(filtered_entries) == 2

    # Assert content and hash for each entry
    entry_v1 = next(e for e in filtered_entries if e.constitution_hash == constitution_hash_v1)
    entry_v2 = next(e for e in filtered_entries if e.constitution_hash == constitution_hash_v2)

    assert entry_v1.constitution_content == constitution_content_v1
    assert entry_v2.constitution_content == constitution_content_v2

    # Assert that the timestamps are in the correct order (v1 before v2)
    assert entry_v1.registered_at < entry_v2.registered_at
