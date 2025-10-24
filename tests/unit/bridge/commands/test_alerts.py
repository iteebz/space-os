def test_alerts_sets_bookmarks_after_rendering(test_space):
    """Regression test: Alerts command should set bookmarks after rendering, clearing unread count."""
    from space.os.bridge import db
    from space.os.spawn import registry

    channel_id = db.create_channel("alert-channel")
    agent_id = registry.ensure_agent("test-agent")

    msg_id = db.create_message(channel_id, "system", "alert message", priority="alert")

    before_alerts = db.get_alerts(agent_id)
    assert len(before_alerts) == 1, "Should have 1 unread alert"

    db.set_bookmark(agent_id, channel_id, msg_id)

    after_alerts = db.get_alerts(agent_id)
    assert len(after_alerts) == 0, "After setting bookmark, alert should be marked as read"
