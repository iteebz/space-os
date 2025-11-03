from datetime import datetime, timedelta

from space.lib.format import format_duration, humanize_timestamp
from space.os.memory.format import format_memory_entries


def test_humanize_timestamp_recent():
    now = datetime.now().isoformat()
    assert humanize_timestamp(now) == "just now"


def test_humanize_timestamp_old():
    old = (datetime.now() - timedelta(days=400)).isoformat()
    assert "year" in humanize_timestamp(old)


def test_humanize_timestamp_empty():
    assert humanize_timestamp("") == "never"


def test_format_duration_seconds():
    assert format_duration(45) == "45s"


def test_format_duration_complex():
    assert format_duration(90000) == "1d 1h"


def test_format_memory_entries_basic():
    class Entry:
        topic = "test"
        memory_id = "abc12345def"
        created_at = datetime.now().isoformat()
        message = "msg"
        core = False
        archived_at = None

    result = format_memory_entries([Entry()])
    assert "# test" in result
    assert "msg" in result
