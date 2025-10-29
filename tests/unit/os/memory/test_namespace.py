from unittest.mock import MagicMock, patch

import pytest
import typer

from space.os.memory.ops import namespace as ops_namespace


@pytest.fixture
def mock_memory_api():
    with patch("space.os.memory.ops.namespace.api") as mock_api:
        yield mock_api


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=typer.Context)
    ctx.obj = {"identity": "test_agent", "json": False, "quiet": False, "all": False}
    return ctx


def test_add_entry(mock_memory_api, mock_ctx):
    mock_entry = MagicMock(uuid="test-uuid")
    mock_memory_api.add_entry.return_value = mock_entry
    result = ops_namespace.add_entry(mock_ctx, "journal", "test message")
    mock_memory_api.add_entry.assert_called_once_with(
        agent_id="test_agent", topic="journal", message="test message", source="manual"
    )
    assert result == mock_entry


def test_list_entries(mock_memory_api, mock_ctx):
    mock_entries = [MagicMock()]
    mock_memory_api.list_entries.return_value = mock_entries
    result = ops_namespace.list_entries(mock_ctx, "journal", show_all=False)
    mock_memory_api.list_entries.assert_called_once_with(
        agent_id="test_agent", topic="journal", show_all=False
    )
    assert result == mock_entries


def test_archive_entry(mock_memory_api, mock_ctx):
    mock_memory_api.get_by_id.return_value = MagicMock(
        agent_id="test_agent", topic="journal", uuid="some-long-test-uuid"
    )
    result = ops_namespace.archive_entry(mock_ctx, "some-long-test-uuid", restore=False)
    mock_memory_api.archive_entry.assert_called_once_with("some-long-test-uuid")
    assert result == "archived"


def test_restore_entry(mock_memory_api, mock_ctx):
    mock_memory_api.get_by_id.return_value = MagicMock(
        agent_id="test_agent", topic="journal", uuid="some-long-test-uuid"
    )
    result = ops_namespace.archive_entry(mock_ctx, "some-long-test-uuid", restore=True)
    mock_memory_api.restore_entry.assert_called_once_with("some-long-test-uuid")
    assert result == "restored"


def test_core_entry(mock_memory_api, mock_ctx):
    mock_memory_api.get_by_id.return_value = MagicMock(
        agent_id="test_agent", topic="journal", uuid="some-long-test-uuid"
    )
    result = ops_namespace.core_entry(mock_ctx, "some-long-test-uuid", unmark=False)
    mock_memory_api.mark_core.assert_called_once_with("some-long-test-uuid", core=True)
    assert result is True


def test_uncore_entry(mock_memory_api, mock_ctx):
    mock_memory_api.get_by_id.return_value = MagicMock(
        agent_id="test_agent", topic="journal", uuid="some-long-test-uuid"
    )
    result = ops_namespace.core_entry(mock_ctx, "some-long-test-uuid", unmark=True)
    mock_memory_api.mark_core.assert_called_once_with("some-long-test-uuid", core=False)
    assert result is False


def test_replace_entry(mock_memory_api, mock_ctx):
    mock_memory_api.get_by_id.return_value = MagicMock(
        agent_id="test_agent", topic="journal", uuid="some-long-old-uuid"
    )
    mock_memory_api.replace_entry.return_value = "some-long-new-uuid"
    result = ops_namespace.replace_entry(mock_ctx, "some-long-old-uuid", "new message", "test note")
    mock_memory_api.replace_entry.assert_called_once_with(
        ["some-long-old-uuid"], "test_agent", "journal", "new message", "test note"
    )
    assert result == "some-long-new-uuid"


def test_missing_identity_raises_error(mock_memory_api):
    ctx = MagicMock(spec=typer.Context)
    ctx.obj = {"json": False, "quiet": False, "all": False}
    with pytest.raises(
        typer.BadParameter, match="Agent identity must be provided via --as option."
    ):
        ops_namespace.add_entry(ctx, "journal", "test message")
