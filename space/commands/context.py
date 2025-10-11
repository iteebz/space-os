"""Unified concept retrieval: evolution + current state + lattice."""

import json
from datetime import datetime

import typer

from ..bridge import config as bridge_config
from ..events import DB_PATH
from ..knowledge import db as knowledge_db
from ..lib import db as libdb
from ..lib import readme
from ..memory import db as memory_db


def context(
    topic: str | None = typer.Argument(None, help="Topic to retrieve context for"),
    identity: str | None = typer.Option(None, "--as", help="Scope to identity (default: all)"),
    all_agents: bool = typer.Option(False, "--all", help="Cross-agent perspective"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Unified context retrieval: trace evolution + current state + lattice docs."""

    if not topic:
        try:
            from pathlib import Path

            readme_path = Path(__file__).parent / "README.context.md"
            typer.echo(readme_path.read_text())
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ context README not found: {e}")
        return

    timeline = _collect_timeline(topic, identity, all_agents)
    current_state = _collect_current_state(topic, identity, all_agents)
    lattice_docs = _search_lattice(topic)

    if json_output:
        typer.echo(
            json.dumps({"evolution": timeline, "state": current_state, "lattice": lattice_docs})
        )
        return

    if quiet_output:
        return

    if timeline:
        typer.echo("## EVOLUTION (last 10)\n")
        for entry in timeline:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
            typ = entry["type"]
            identity_str = entry["identity"] or "system"
            data = entry["data"][:100] if entry["data"] else ""
            typer.echo(f"[{ts}] {typ} ({identity_str})")
            typer.echo(f"  {data}\n")

    if current_state["memory"] or current_state["knowledge"] or current_state["bridge"]:
        typer.echo("\n## CURRENT STATE\n")

        if current_state["memory"]:
            typer.echo(f"memory: {len(current_state['memory'])}")
            for r in current_state["memory"][:5]:
                typer.echo(f"  {r['topic']}: {r['message'][:80]}")
            typer.echo()

        if current_state["knowledge"]:
            typer.echo(f"knowledge: {len(current_state['knowledge'])}")
            for r in current_state["knowledge"][:5]:
                typer.echo(f"  {r['domain']}: {r['content'][:80]}")
            typer.echo()

        if current_state["bridge"]:
            typer.echo(f"bridge: {len(current_state['bridge'])}")
            for r in current_state["bridge"][:5]:
                typer.echo(f"  [{r['channel']}] {r['content'][:80]}")
            typer.echo()

    if lattice_docs:
        typer.echo("\n## LATTICE DOCS\n")
        for heading, content in lattice_docs.items():
            typer.echo(f"### {heading}\n")
            preview = "\n".join(content.split("\n")[:5])
            typer.echo(f"{preview}...\n")

    if not timeline and not any(current_state.values()) and not lattice_docs:
        typer.echo(f"No context found for '{topic}'")


def _query_with_identity(base_query: str, params: list, identity: str | None, all_agents: bool):
    if identity and not all_agents:
        base_query += " AND agent_id = ?"
        params.append(identity)
    return base_query, params


def _collect_timeline(topic: str, identity: str | None, all_agents: bool):
    from ..spawn import registry

    timeline = []
    seen_hashes = set()

    noise_events = {
        "bridge.message_received",
        "bridge.message_sending",
        "events.bridge.message_received",
        "events.bridge.message_sending",
        "events.memory.entry.add",
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
                        "identity": registry.get_agent_name(row[2]) or row[2] if row[2] else None,
                        "data": row[4],
                        "timestamp": row[5],
                    }
                )

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
            query = "SELECT agent_id, topic, message, created_at FROM memory WHERE (message LIKE ? OR topic LIKE ?)"
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
                        "identity": registry.get_agent_name(row[0]) or row[0] if row[0] else None,
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
                        "identity": registry.get_agent_name(row[2]) or row[2] if row[2] else None,
                        "data": row[1],
                        "timestamp": row[3] if isinstance(row[3], int) else 0,
                    }
                )

    if bridge_config.DB_PATH.exists():
        with libdb.connect(bridge_config.DB_PATH) as conn:
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
                        "identity": registry.get_agent_name(row[1]) or row[1] if row[1] else None,
                        "data": row[2],
                        "timestamp": ts,
                    }
                )

    timeline.sort(key=lambda x: x["timestamp"])
    return timeline[-10:]


def _collect_current_state(topic: str, identity: str | None, all_agents: bool):
    from ..spawn import registry

    results = {"memory": [], "knowledge": [], "bridge": []}

    if memory_db.database_path().exists():
        with memory_db.connect() as conn:
            query = "SELECT agent_id, topic, message FROM memory WHERE message LIKE ?"
            params = [f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["memory"] = [
                {"identity": registry.get_agent_name(r[0]) or r[0], "topic": r[1], "message": r[2]}
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
                    "contributor": registry.get_agent_name(r[2]) or r[2],
                }
                for r in rows
            ]

    if bridge_config.DB_PATH.exists():
        with libdb.connect(bridge_config.DB_PATH) as conn:
            query = "SELECT c.name, m.agent_id, m.content FROM messages m JOIN channels c ON m.channel_id = c.id WHERE m.content LIKE ?"
            params = [f"%{topic}%"]
            query, params = _query_with_identity(query, params, identity, all_agents)
            rows = conn.execute(query, params).fetchall()
            results["bridge"] = [
                {"channel": r[0], "sender": registry.get_agent_name(r[1]) or r[1], "content": r[2]}
                for r in rows
            ]

    return results


def _search_lattice(topic: str):
    """Search README for relevant sections."""
    try:
        content = readme.README.read_text()
        lines = content.split("\n")
        matches = {}

        for line in lines:
            if line.startswith("#") and topic.lower() in line.lower():
                heading = line.strip()
                try:
                    section_content = readme.load_section(heading)
                    matches[heading] = section_content
                except ValueError:
                    pass

        return matches
    except Exception:
        return {}
