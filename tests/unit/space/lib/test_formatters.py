from space.bridge.models import Channel
from space.lib import formatters


def test_format_channel_row_with_activity():
    channel = Channel(
        name="test-channel",
        topic="Test topic",
        created_at="2025-01-01 10:00:00",
        participants=["alice", "bob"],
        message_count=5,
        last_activity="2025-01-02 15:30:00",
        unread_count=2,
        notes_count=1,
    )
    last_activity, description = formatters.format_channel_row(channel)
    assert "Jan 02" in last_activity or "2025-01-02" in last_activity
    assert "test-channel" in description
    assert "5 msgs" in description
    assert "2 members" in description


def test_format_channel_row_no_activity():
    channel = Channel(
        name="new-channel",
        topic=None,
        created_at="2025-01-01 10:00:00",
        participants=[],
        message_count=0,
        last_activity=None,
        unread_count=0,
        notes_count=0,
    )
    last_activity, description = formatters.format_channel_row(channel)
    assert last_activity
    assert "new-channel" in description
