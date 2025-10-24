import logging
from datetime import datetime

from space.os import bridge, config, db, events, knowledge, memory, spawn

log = logging.getLogger(__name__)

_MAX_SEARCH_LEN = 256


def _get_max_search_len() -> int:
    """Get max search length from config with security warning if reduced."""
    cfg = config.load_config()
    max_len = cfg.get("search", {}).get("max_length", _MAX_SEARCH_LEN)
    if max_len < _MAX_SEARCH_LEN:
        log.warning(f"Search limit {max_len} below {_MAX_SEARCH_LEN} may allow ReDoS attacks")
    return max_len


def _validate_search_term(term: str) -> None:
    """Validate search term to prevent DoS via oversized patterns."""
    max_len = _get_max_search_len()
    if len(term) > max_len:
        raise ValueError(f"Search term too long (max {max_len} chars, got {len(term)})")


def _query_with_identity(base_query: str, params: list, identity: str | None, all_agents: bool):
    if identity and not all_agents:
        agent_id = spawn.db.get_agent_id(identity)
        if not agent_id:
            raise ValueError(f"Agent '{identity}' not found")
        base_query += " AND agent_id = ?"
        params.append(agent_id)
    return base_query, params


def collect_timeline(topic: str, identity: str | None, all_agents: bool):
    _validate_search_term(topic)
    timeline = []
    seen_hashes = set()

    noise_events = {
        "bridge.message_received",
        "bridge.message_sending",
        "events.bridge.message_received",
        "events.bridge.message_sending",
        "events.memory.add",
        "events.memory.summary.set",
        "events.memory.summary.replace",
    }

    if events.path().exists():
        with db.ensure("events") as conn:
            query = (
                "SELECT source, agent_id, event_type, data, timestamp FROM events WHERE data LIKE ?"
            )
            params = [f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            query += " ORDER BY timestamp ASC"

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                event_type = f"{row[0]}.{row[2]}"
                if event_type in noise_events:
                    continue

                data_hash = hash((row[3], row[1]))
                if data_hash in seen_hashes:
                    continue
                seen_hashes.add(data_hash)

                timeline.append(
                    {
                        "source": "events",
                        "type": event_type,
                        "identity": spawn.db.get_agent_name(row[1]) or row[1] if row[1] else None,
                        "data": row[3],
                        "timestamp": row[4],
                    }
                )

    if memory.db.path().exists():
        with db.ensure("memory") as conn:
            query = "SELECT agent_id, topic, message, created_at FROM memories WHERE (message LIKE ? OR topic LIKE ?)"
            params = [f"%{topic}%", f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            query += " ORDER BY created_at ASC"

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                data_hash = hash((row[2], row[0]))
                if data_hash in seen_hashes:
                    continue
                seen_hashes.add(data_hash)

                timeline.append(
                    {
                        "source": "memory",
                        "type": row[1],
                        "identity": spawn.db.get_agent_name(row[0]) or row[0] if row[0] else None,
                        "data": row[2],
                        "timestamp": row[3] if isinstance(row[3], int) else 0,
                    }
                )

    if knowledge.db.path().exists():
        with db.ensure("knowledge") as conn:
            query = "SELECT domain, content, agent_id, created_at FROM knowledge WHERE (content LIKE ? OR domain LIKE ?)"
            params = [f"%{topic}%", f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            query += " ORDER BY created_at ASC"

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                data_hash = hash((row[1], row[2]))
                if data_hash in seen_hashes:
                    continue
                seen_hashes.add(data_hash)

                timeline.append(
                    {
                        "source": "knowledge",
                        "type": row[0],
                        "identity": spawn.db.get_agent_name(row[2]) or row[2] if row[2] else None,
                        "data": row[1],
                        "timestamp": row[3] if isinstance(row[3], int) else 0,
                    }
                )
    if bridge.db.path().exists():
        with db.ensure("bridge") as conn:
            query = "SELECT c.name, m.agent_id, m.content, m.created_at FROM messages m JOIN channels c ON m.channel_id = c.channel_id WHERE (m.content LIKE ? OR c.name LIKE ?)"
            params = [f"%{topic}%", f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            query += " ORDER BY m.created_at ASC"

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                data_hash = hash((row[2], row[1]))
                if data_hash in seen_hashes:
                    continue
                seen_hashes.add(data_hash)

                ts = 0
                if row[3]:
                    try:
                        ts = int(datetime.fromisoformat(row[3]).timestamp())
                    except (ValueError, TypeError):
                        ts = row[3] if isinstance(row[3], int) else 0
                timeline.append(
                    {
                        "source": "bridge",
                        "type": row[0],
                        "identity": spawn.db.get_agent_name(row[1]) or row[1] if row[1] else None,
                        "data": row[2],
                        "timestamp": ts,
                    }
                )

    timeline.sort(key=lambda x: x["timestamp"])
    return timeline[-10:]


def collect_current_state(topic: str, identity: str | None, all_agents: bool):
    results = {"memory": [], "knowledge": [], "bridge": []}

    if memory.db.path().exists():
        with db.ensure("memory") as conn:
            query = "SELECT agent_id, topic, message FROM memories WHERE message LIKE ?"
            params = [
                f"%{topic}%",
            ]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["memory"] = [
                {"identity": spawn.db.get_agent_name(r[0]) or r[0], "topic": r[1], "message": r[2]}
                for r in rows
            ]

    if knowledge.db.path().exists():
        with db.ensure("knowledge") as conn:
            query = "SELECT domain, content, agent_id FROM knowledge WHERE (content LIKE ? OR domain LIKE ?)"
            params = [f"%{topic}%", f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["knowledge"] = [
                {
                    "domain": r[0],
                    "content": r[1],
                    "contributor": spawn.db.get_agent_name(r[2]) or r[2],
                }
                for r in rows
            ]

    if bridge.db.path().exists():
        with db.ensure("bridge") as conn:
            query = "SELECT c.name, m.agent_id, m.content FROM messages m JOIN channels c ON m.channel_id = c.channel_id WHERE m.content LIKE ?"
            params = [
                f"%{topic}%",
            ]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["bridge"] = [
                {"channel": r[0], "sender": spawn.db.get_agent_name(r[1]) or r[1], "content": r[2]}
                for r in rows
            ]

    return results
