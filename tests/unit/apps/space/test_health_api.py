from __future__ import annotations

import sqlite3

from space.apps.space.api import health as health_api
from space.lib import paths, store


def test_health_check_reports_ok(test_space):
    ok, issues, counts = health_api.check_db()

    assert ok is True

    assert issues == []

    assert set(counts) == health_api.EXPECTED_TABLES

    assert all(count == 0 for count in counts.values())

    store.close_all()


def test_health_check_detects_missing_db(test_space):
    store.close_all()

    db_path = paths.dot_space() / health_api.DB_NAME
    db_path.unlink()

    ok, issues, counts = health_api.check_db()

    assert ok is False
    assert any("missing" in issue for issue in issues)
    assert counts == {}


def test_health_check_detects_fk_violation(test_space):
    channel_id = "channel-1"
    message_id = "ghost-message"
    missing_agent = "agent-ghost"

    with store.ensure() as conn:
        conn.execute(
            """
            INSERT INTO channels (channel_id, name, created_at)
            VALUES (?, ?, STRFTIME('%Y-%m-%dT%H:%M:%f', 'now'))
            """,
            (
                channel_id,
                "Bridge",
            ),
        )

    store.close_all()

    db_path = paths.dot_space() / health_api.DB_NAME
    raw = sqlite3.connect(db_path)
    try:
        raw.execute("PRAGMA foreign_keys = OFF")
        raw.execute(
            """
            INSERT INTO messages (message_id, channel_id, agent_id, content, created_at)
            VALUES (?, ?, ?, ?, STRFTIME('%Y-%m-%dT%H:%M:%f', 'now'))
            """,
            (
                message_id,
                channel_id,
                missing_agent,
                "orphan",
            ),
        )
        raw.commit()
    finally:
        raw.close()

    ok, issues, counts = health_api.check_db()

    assert ok is False
    assert any("messages" in issue for issue in issues)
    assert "messages" in counts and counts["messages"] >= 1
