from space.bridge.api import channels


def test_with_prefix_flag(test_space):
    from typer.testing import CliRunner

    from space.bridge.app import app as bridge_app

    runner = CliRunner()

    channels.create_channel("protoss-arbiter")
    channels.create_channel("protoss-ascension")
    channels.create_channel("bridge-context")
    channels.create_channel("bridge-meta")
    channels.create_channel("space-feedback")
    channels.create_channel("random-channel")

    result = runner.invoke(bridge_app, ["--quiet", "archive", "protoss-", "bridge-", "--prefix"])
    assert result.exit_code == 0

    all_channels = channels.all_channels()
    archived = [c.name for c in all_channels if c.archived_at]
    active = [c.name for c in all_channels if not c.archived_at]

    assert "protoss-arbiter" in archived
    assert "protoss-ascension" in archived
    assert "bridge-context" in archived
    assert "bridge-meta" in archived

    assert "space-feedback" in active
    assert "random-channel" in active


def test_without_prefix_flag(test_space):
    from typer.testing import CliRunner

    from space.bridge.app import app as bridge_app

    runner = CliRunner()

    channels.create_channel("protoss-arbiter")
    channels.create_channel("random-channel")
    channels.create_channel("space-feedback")

    result = runner.invoke(bridge_app, ["--quiet", "archive", "random-channel"])
    assert result.exit_code == 0

    all_channels = channels.all_channels()
    archived = [c.name for c in all_channels if c.archived_at]

    assert "random-channel" in archived
    assert "protoss-arbiter" not in archived
    assert "space-feedback" not in archived
