"""Bridge stats API contract tests."""

from unittest.mock import MagicMock, patch

import pytest

from space.core import bridge


def make_mock_row(data):
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def mock_db():
    conn = MagicMock()
    with patch("space.lib.store.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = conn
        mock_ensure.return_value.__exit__.return_value = None
        yield conn


def test_stats_returns_dict(mock_db):
    mock_db.execute.return_value.fetchone.return_value = (0,)
    mock_db.execute.return_value.fetchall.return_value = []

    result = bridge.stats()
    assert isinstance(result, dict)
    assert "channels" in result
    assert "messages" in result
