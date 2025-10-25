from unittest.mock import MagicMock, patch

from space.os.core.bridge.api import spawning


@patch("space.os.core.bridge.api.spawning.config.load_config")
@patch("space.os.core.bridge.api.spawning.subprocess.run")
def test_spawn_from_mention_with_context(mock_run, mock_config):
    """Spawn from mention exports channel and injects context."""
    mock_config.return_value = {"roles": {"zealot": {}}}
    export_result = MagicMock()
    export_result.returncode = 0
    export_result.stdout = "# test-channel\n\n[alice] hello world\n"
    mock_run.return_value = export_result

    result = spawning._build_prompt("zealot", "test-channel", "@zealot what is 2+2?")

    assert result is not None
    assert "hello world" in result
    assert "what is 2+2?" in result
    assert "[SPACE INSTRUCTIONS]" in result

    assert mock_run.call_count == 1
    export_call = mock_run.call_args_list[0]
    assert export_call[0][0] == ["bridge", "export", "test-channel"]


@patch("space.os.core.bridge.ops.spawning.subprocess.run")
def test_spawn_from_mention_export_fails(mock_run):
    """Spawn fails gracefully if export fails."""
    export_result = MagicMock()
    export_result.returncode = 1
    mock_run.return_value = export_result

    result = spawning._build_prompt("zealot", "test-channel", "@zealot something")

    assert result is None


@patch("space.os.core.bridge.ops.spawning.config.load_config")
@patch("space.os.core.bridge.ops.spawning.subprocess.run")
def test_spawn_from_mention_returns_prompt(mock_run, mock_config):
    """Spawn from mention returns prompt for worker to execute."""
    mock_config.return_value = {"roles": {"zealot": {}}}
    export_result = MagicMock()
    export_result.returncode = 0
    export_result.stdout = "# channel\n"
    mock_run.return_value = export_result

    result = spawning._build_prompt("zealot", "test-channel", "@zealot something")

    assert result is not None
    assert "[SPACE INSTRUCTIONS]" in result


@patch("space.os.core.bridge.ops.spawning.subprocess.run")
def test_spawn_from_mention_invalid_identity(mock_run):
    """Spawn skipped for invalid identities."""
    result = spawning._build_prompt("nonexistent", "test-channel", "@nonexistent do something")

    assert result is None
    mock_run.assert_not_called()
