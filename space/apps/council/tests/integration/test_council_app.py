"""Integration tests for council command."""

import pytest
from unittest.mock import Mock

from space.apps.council.app import council


def test_council_command_creates_instance(monkeypatch):
    """council() creates Council instance and runs it."""
    mock_council_class = Mock()
    mock_council = Mock()
    mock_council_class.return_value = mock_council

    monkeypatch.setattr("space.apps.council.app.Council", mock_council_class)
    monkeypatch.setattr("asyncio.run", Mock())

    council(channel="test-channel")

    mock_council_class.assert_called_with("test-channel")
