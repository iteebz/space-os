"""Bridge stats aggregation: messages, channels, notes, and events."""

from space.lib import store


def stats() -> dict:
    """Get bridge statistics: messages, channels, notes, and events by agent."""
    with store.ensure("bridge") as conn:
        total_msgs = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        archived_msgs = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE channel_id IN (SELECT channel_id FROM channels WHERE archived_at IS NOT NULL)"
        ).fetchone()[0]
        active_msgs = total_msgs - archived_msgs

        total_channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        active_channels = conn.execute(
            "SELECT COUNT(*) FROM channels WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived_channels = total_channels - active_channels

        distinct_channels = conn.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM messages WHERE channel_id IS NOT NULL"
        ).fetchone()[0]

        total_notes = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]

        msg_by_agent = conn.execute(
            "SELECT agent_id, COUNT(*) as count FROM messages GROUP BY agent_id ORDER BY count DESC"
        ).fetchall()

    try:
        with store.ensure("events") as conn:
            rows = conn.execute(
                "SELECT agent_id, event_type, timestamp FROM events ORDER BY timestamp"
            ).fetchall()

            agent_events: dict[str, dict] = {}
            total_events = len(rows)

            for row in rows:
                agent_id = row[0]
                event_type = row[1]
                timestamp = row[2]

                if agent_id not in agent_events:
                    agent_events[agent_id] = {
                        "events": 0,
                        "spawns": 0,
                        "last_active": None,
                    }

                agent_events[agent_id]["events"] += 1
                if event_type == "session_start":
                    agent_events[agent_id]["spawns"] += 1
                agent_events[agent_id]["last_active"] = timestamp

            events_by_agent = [
                {"agent_id": agent_id, **data} for agent_id, data in agent_events.items()
            ]
    except Exception:
        total_events = 0
        events_by_agent = []

    return {
        "messages": {
            "total": total_msgs,
            "active": active_msgs,
            "archived": archived_msgs,
            "by_agent": [{"agent_id": row[0], "count": row[1]} for row in msg_by_agent],
        },
        "channels": {
            "total": distinct_channels,
            "active": active_channels,
            "archived": archived_channels,
        },
        "notes": total_notes,
        "events": {
            "total": total_events,
            "by_agent": events_by_agent,
        },
    }
