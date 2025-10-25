import subprocess
import sys
from unittest.mock import patch

from space.core.spawn import scripts


@patch("subprocess.run")
def test_gemini(mock_run):
    scripts.gemini()
    mock_run.assert_called_once_with(
        ["poetry", "run", "spawn", "launch", "harbinger", "--agent", "gemini"],
        check=True,
    )


@patch("subprocess.run")
def test_claude(mock_run):
    scripts.claude()
    mock_run.assert_called_once_with(
        ["poetry", "run", "spawn", "launch", "zealot", "--agent", "claude"],
        check=True,
    )


@patch("subprocess.run")
def test_codex(mock_run):
    scripts.codex()
    mock_run.assert_called_once_with(
        ["poetry", "run", "spawn", "launch", "sentinel", "--agent", "codex"],
        check=True,
    )


@patch("subprocess.run")
@patch("sys.exit")
def test_run_launch_process_error(mock_exit, mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
    scripts._run_launch("role", "agent")
    mock_exit.assert_called_once_with(1)


@patch("subprocess.run")
@patch("sys.exit")
@patch("builtins.print")
def test_run_launch_file_not_found(mock_print, mock_exit, mock_run):
    mock_run.side_effect = FileNotFoundError
    scripts._run_launch("role", "agent")
    mock_exit.assert_called_once_with(1)
    mock_print.assert_called_once_with(
        "Error: 'poetry' command not found. Is poetry installed and in your PATH?",
        file=sys.stderr,
    )
