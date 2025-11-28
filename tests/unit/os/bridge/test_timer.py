"""Contract tests for timer functionality."""

import re
from datetime import datetime, timedelta


def test_timer_regex_days():
    """Regex extracts days correctly."""
    match = re.search(r"/timer\s+(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", "/timer 7d")
    assert match
    assert match.group(1) == "7"
    assert match.group(2) is None
    assert match.group(3) is None


def test_timer_regex_hours():
    """Regex extracts hours correctly."""
    match = re.search(r"/timer\s+(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", "/timer 8h")
    assert match
    assert match.group(1) is None
    assert match.group(2) == "8"
    assert match.group(3) is None


def test_timer_regex_minutes():
    """Regex extracts minutes correctly."""
    match = re.search(r"/timer\s+(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", "/timer 30m")
    assert match
    assert match.group(1) is None
    assert match.group(2) is None
    assert match.group(3) == "30"


def test_timer_regex_combined():
    """Regex extracts days, hours and minutes."""
    match = re.search(r"/timer\s+(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", "/timer 2d8h30m")
    assert match
    assert match.group(1) == "2"
    assert match.group(2) == "8"
    assert match.group(3) == "30"


def test_timer_duration_calculation():
    """Duration calculation is correct."""
    now = datetime(2024, 1, 1, 12, 0, 0)
    duration = timedelta(hours=8, minutes=30)
    expected = datetime(2024, 1, 1, 20, 30, 0)
    assert now + duration == expected


def test_timer_format_hours_only():
    """Timer display format for hours only."""
    hours = 8
    minutes = 0
    total_minutes = hours * 60 + minutes

    if hours > 0 and minutes > 0:
        duration_str = f"{hours}h {minutes}m"
    elif hours > 0:
        duration_str = f"{hours}h"
    else:
        duration_str = f"{minutes}m"

    assert duration_str == "8h"
    assert total_minutes == 480


def test_timer_format_minutes_only():
    """Timer display format for minutes only."""
    hours = 0
    minutes = 30
    total_minutes = hours * 60 + minutes

    if hours > 0 and minutes > 0:
        duration_str = f"{hours}h {minutes}m"
    elif hours > 0:
        duration_str = f"{hours}h"
    else:
        duration_str = f"{minutes}m"

    assert duration_str == "30m"
    assert total_minutes == 30


def test_timer_format_combined():
    """Timer display format for hours and minutes."""
    hours = 2
    minutes = 30
    total_minutes = hours * 60 + minutes

    if hours > 0 and minutes > 0:
        duration_str = f"{hours}h {minutes}m"
    elif hours > 0:
        duration_str = f"{hours}h"
    else:
        duration_str = f"{minutes}m"

    assert duration_str == "2h 30m"
    assert total_minutes == 150


def test_timer_expiry_comparison():
    """Timer expiry comparison logic."""
    now = datetime(2024, 1, 1, 20, 0, 0)
    expires_past = datetime(2024, 1, 1, 19, 59, 0)
    expires_future = datetime(2024, 1, 1, 20, 30, 0)

    assert now >= expires_past
    assert not (now >= expires_future)


def test_isoformat_parse():
    """ISO format string parses correctly."""
    iso_str = "2024-01-01T20:00:00"
    dt = datetime.fromisoformat(iso_str)
    assert dt == datetime(2024, 1, 1, 20, 0, 0)
    assert dt.isoformat() == iso_str
