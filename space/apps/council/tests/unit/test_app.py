"""Tests for Council class."""

import pytest
from unittest.mock import Mock, patch

from space.apps.council.app import Council


def test_initialization(council_instance, mock_channel):
    """Council initializes with channel."""
    assert council_instance.channel_name == mock_channel["channel_name"]
    assert council_instance.channel_id == mock_channel["channel_id"]
    assert council_instance.running is True
    assert council_instance.last_msg_id is None
    assert len(council_instance.sent_msg_ids) == 0


def test_print_message_formats(council_instance, mock_messages, monkeypatch):
    """_print_message formats identity, timestamp, and prefix."""
    monkeypatch.setattr(
        "space.spawn.registry.get_identity",
        lambda x: "alice" if x == "agent-1" else x,
    )

    output = []
    def capture_print(*args, **kwargs):
        output.append(args[0])

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_message(mock_messages[0])

    assert "alice" in output[0]
    assert "First message" in output[0]
    assert "←" in output[0]


def test_print_message_agent_prefix(council_instance, mock_messages, monkeypatch):
    """_print_message uses ← for agent messages."""
    monkeypatch.setattr(
        "space.spawn.registry.get_identity",
        lambda x: "bob" if x == "agent-2" else x,
    )

    output = []
    def capture_print(*args, **kwargs):
        output.append(args[0])

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_message(mock_messages[1])

    assert "←" in output[0]
    assert "bob" in output[0]


def test_print_message_human_prefix(council_instance, monkeypatch):
    """_print_message uses → for human messages."""
    human_msg = Mock()
    human_msg.agent_id = "human"
    human_msg.content = "Input"
    human_msg.created_at = "2025-10-24T10:00:00"

    monkeypatch.setattr(
        "space.spawn.registry.get_identity",
        lambda x: "human",
    )

    output = []
    def capture_print(*args, **kwargs):
        output.append(args[0])

    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_message(human_msg)

    assert "→" in output[0]


def test_print_error_writes_stderr(council_instance):
    """_print_error writes to stderr."""
    output = []
    def capture_print(*args, **kwargs):
        output.append((args, kwargs))

    import sys
    with patch("builtins.print", side_effect=capture_print):
        council_instance._print_error("Test error")

    assert len(output) == 1
    assert "Test error" in output[0][0][0]
    assert output[0][1].get("file") == sys.stderr
