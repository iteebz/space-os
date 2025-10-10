import json
import tempfile
from pathlib import Path

import pytest

from space.memory import db
from space.spawn import config as spawn_config


@pytest.fixture
def in_memory_db():
    # Use a temporary directory for the database file
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "memory.db"
        spawn_config.workspace_root = lambda: Path(tmpdir)

        # Ensure the database is initialized
        db.connect()

        yield db_path


def test_add_checkpoint_entry(in_memory_db):
    identity = "test-agent"
    topic = "test-checkpoint"
    message = "This is a checkpoint message."
    bridge_channel = "test-channel"
    code_anchors = json.dumps(
        [{"file": "test.py", "line": 1, "fn": "test_func", "purpose": "test", "status": "new"}]
    )

    db.add_checkpoint_entry(identity, topic, message, bridge_channel, code_anchors)

    entries = db.get_entries(identity, topic)
    assert len(entries) == 1
    entry = entries[0]

    assert entry.identity == identity
    assert entry.topic == topic
    assert entry.message == message
    assert entry.source == "checkpoint"
    assert entry.bridge_channel == bridge_channel
    assert entry.code_anchors == code_anchors
    assert entry.core is False
