import contextlib

import pytest

from space.bridge.api import channels


@pytest.fixture
def setup_prefix_channels():
    test_channels = [
        "protoss-arbiter",
        "protoss-ascension",
        "bridge-context",
        "bridge-meta",
        "space-feedback",
        "random-channel",
    ]
    
    for name in test_channels:
        with contextlib.suppress(Exception):
            channels.delete_channel(name)
    
    created = []
    for name in test_channels:
        cid = channels.create_channel(name)
        created.append((name, cid))
    
    yield created
    
    for name, _ in created:
        with contextlib.suppress(Exception):
            channels.delete_channel(name)


def test_archive_with_prefix_flag(setup_prefix_channels):
    from space.bridge.commands.channels import archive
    from unittest.mock import MagicMock
    
    mock_ctx = MagicMock()
    
    archive(
        channels=["protoss-", "bridge-"],
        prefix=True,
        json_output=False,
        quiet_output=True,
    )
    
    all_channels = channels.all_channels()
    archived = [c.name for c in all_channels if c.archived_at]
    active = [c.name for c in all_channels if not c.archived_at]
    
    assert "protoss-arbiter" in archived
    assert "protoss-ascension" in archived
    assert "bridge-context" in archived
    assert "bridge-meta" in archived
    
    assert "space-feedback" in active
    assert "random-channel" in active


def test_archive_without_prefix_flag(setup_prefix_channels):
    from space.bridge.commands.channels import archive
    
    archive(
        channels=["random-channel"],
        prefix=False,
        json_output=False,
        quiet_output=True,
    )
    
    all_channels = channels.all_channels()
    archived = [c.name for c in all_channels if c.archived_at]
    
    assert "random-channel" in archived
    assert "protoss-arbiter" not in archived
    assert "space-feedback" not in archived
