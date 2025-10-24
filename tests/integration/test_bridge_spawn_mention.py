from unittest.mock import MagicMock, patch

from space.os.bridge import parser


@patch("space.os.bridge.parser.subprocess.run")
def test_spawn_from_mention_with_context(mock_run):
    """Spawn from mention exports channel and injects context."""
    # Mock bridge export
    export_result = MagicMock()
    export_result.returncode = 0
    export_result.stdout = "# test-channel\n\n[alice] hello world\n"

    # Only export should be called (worker does the spawn)
    mock_run.return_value = export_result

    result = parser.spawn_from_mention("hailot", "test-channel", "@hailot what is 2+2?")

    # Result is the prompt, not the response
    assert result is not None
    assert "hello world" in result  # context included
    assert "what is 2+2?" in result  # task included
    assert "[SPACE INSTRUCTIONS]" in result

    # Verify bridge export was called
    assert mock_run.call_count == 1
    export_call = mock_run.call_args_list[0]
    assert export_call[0][0] == ["bridge", "export", "test-channel"]


@patch("space.os.bridge.parser.subprocess.run")
def test_spawn_from_mention_export_fails(mock_run):
    """Spawn fails gracefully if export fails."""
    export_result = MagicMock()
    export_result.returncode = 1

    mock_run.return_value = export_result

    result = parser.spawn_from_mention("hailot", "test-channel", "@hailot something")

    assert result is None


@patch("space.os.bridge.parser.subprocess.run")
def test_spawn_from_mention_returns_prompt(mock_run):
    """Spawn from mention returns prompt for worker to execute."""
    export_result = MagicMock()
    export_result.returncode = 0
    export_result.stdout = "# channel\n"

    mock_run.return_value = export_result

    result = parser.spawn_from_mention("hailot", "test-channel", "@hailot something")

    assert result is not None
    assert "[SPACE INSTRUCTIONS]" in result


@patch("space.os.bridge.parser.subprocess.run")
def test_spawn_from_mention_invalid_identity(mock_run):
    """Spawn skipped for invalid identities."""
    result = parser.spawn_from_mention("nonexistent", "test-channel", "@nonexistent do something")

    assert result is None
    # Should not call subprocess at all
    mock_run.assert_not_called()
