import contextlib

from space.bridge.api import channels


def test_with_prefix_flag(test_space):
    from unittest.mock import MagicMock

    from space.bridge.commands.channels import archive

    # Manually create channels
    channels.create_channel("protoss-arbiter")
    channels.create_channel("protoss-ascension")
    channels.create_channel("bridge-context")
    channels.create_channel("bridge-meta")
    channels.create_channel("space-feedback")
    channels.create_channel("random-channel")

    MagicMock()

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

    # Teardown
    for name in [
        "protoss-arbiter",
        "protoss-ascension",
        "bridge-context",
        "bridge-meta",
        "space-feedback",
        "random-channel",
    ]:
        with contextlib.suppress(Exception):
            channels.delete_channel(name)


def test_without_prefix_flag(test_space):
    from space.bridge.commands.channels import archive

    # Manually create channels
    channels.create_channel("protoss-arbiter")
    channels.create_channel("random-channel")
    channels.create_channel("space-feedback")

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

    # Teardown
    for name in ["protoss-arbiter", "random-channel", "space-feedback"]:
        with contextlib.suppress(Exception):
            channels.delete_channel(name)
