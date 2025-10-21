from datetime import datetime

from ..events import DB_PATH
from ..knowledge import db as knowledge_db
from ..lib import db as libdb
from ..lib import paths
from ..memory import db as memory_db
from ..spawn import registry


def _query_with_identity(base_query: str, params: list, identity: str | None, all_agents: bool):
    if identity and not all_agents:
        agent_id = registry.get_agent_id(identity)
        if not agent_id:
            raise ValueError(f"Agent '{identity}' not found")
        base_query += " AND agent_id = ?"
        params.append(agent_id)
    return base_query, params


def collect_timeline(topic: str, identity: str | None, all_agents: bool):
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

    if DB_PATH.exists():
        with libdb.connect(DB_PATH) as conn:
            query = "SELECT id, source, agent_id, event_type, data, timestamp FROM events WHERE data LIKE ?"
            params = [f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            query += " ORDER BY timestamp ASC"

            rows = conn.execute(query, params).fetchall()
            for row in rows:
                event_type = f"{row[1]}.{row[3]}"
                if event_type in noise_events:
                    continue

                data_hash = hash((row[4], row[2]))
                if data_hash in seen_hashes:
                    continue
                seen_hashes.add(data_hash)

                timeline.append(
                    {
                        "source": "events",
                        "type": event_type,
                        "identity": registry.get_identity(row[2]) or row[2] if row[2] else None,
                        "data": row[4],
                        "timestamp": row[5],
                    }
                )

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
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
                        "identity": registry.get_identity(row[0]) or row[0] if row[0] else None,
                        "data": row[2],
                        "timestamp": row[3] if isinstance(row[3], int) else 0,
                    }
                )

    if knowledge_db.database_path().exists():
        with knowledge_db.connect() as conn:
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
                        "identity": registry.get_identity(row[2]) or row[2] if row[2] else None,
                        "data": row[1],
                        "timestamp": row[3] if isinstance(row[3], int) else 0,
                    }
                )
    bridge_db_path = paths.dot_space() / "bridge.db"
    if bridge_db_path.exists():
        with libdb.connect(bridge_db_path) as conn:
            query = "SELECT c.name, m.agent_id, m.content, m.created_at FROM messages m JOIN channels c ON m.channel_id = c.id WHERE (m.content LIKE ? OR c.name LIKE ?)"
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
                        "identity": registry.get_identity(row[1]) or row[1] if row[1] else None,
                        "data": row[2],
                        "timestamp": ts,
                    }
                )

    timeline.sort(key=lambda x: x["timestamp"])
    return timeline[-10:]


def collect_current_state(topic: str, identity: str | None, all_agents: bool):
    results = {"memory": [], "knowledge": [], "bridge": []}

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
            query = "SELECT agent_id, topic, message FROM memories WHERE message LIKE ?"
            params = [
                f"%{topic}%",
            ]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["memory"] = [
                {"identity": registry.get_identity(r[0]) or r[0], "topic": r[1], "message": r[2]}
                for r in rows
            ]

    if knowledge_db.database_path().exists():
        with knowledge_db.connect() as conn:
            query = "SELECT domain, content, agent_id FROM knowledge WHERE (content LIKE ? OR domain LIKE ?)"
            params = [f"%{topic}%", f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["knowledge"] = [
                {
                    "domain": r[0],
                    "content": r[1],
                    "contributor": registry.get_identity(r[2]) or r[2],
                }
                for r in rows
            ]

    bridge_db_path = paths.dot_space() / "bridge.db"
    if bridge_db_path.exists():
        with libdb.connect(bridge_db_path) as conn:
            query = "SELECT c.name, m.agent_id, m.content FROM messages m JOIN channels c ON m.channel_id = c.id WHERE m.content LIKE ?"
            params = [
                f"%{topic}%",
            ]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["bridge"] = [
                {"channel": r[0], "sender": registry.get_identity(r[1]) or r[1], "content": r[2]}
                for r in rows
            ]

    return results
