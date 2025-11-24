"""Knowledge operations: discovered patterns and insights across domains."""

import re
from datetime import datetime

from space.core.models import Knowledge, SearchResult
from space.core.queries import archive_filter
from space.lib import store
from space.lib.store import from_row
from space.lib.uuid7 import uuid7
from space.os import spawn


def _row_to_knowledge(row: dict) -> Knowledge:
    return from_row(row, Knowledge)


def _validate_domain(domain: str) -> None:
    if not domain:
        raise ValueError("Domain cannot be empty")
    if not re.match(r"^[a-z0-9\-/]+$", domain):
        raise ValueError(
            f"Invalid domain '{domain}': use lowercase letters, numbers, hyphens, and forward slashes"
        )


def add_knowledge(domain: str, agent_id: str, content: str) -> str:
    _validate_domain(domain)
    knowledge_id = uuid7()
    with store.ensure() as conn:
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, domain, agent_id, content) VALUES (?, ?, ?, ?)",
            (knowledge_id, domain, agent_id, content),
        )
    spawn.api.touch_agent(agent_id)
    return knowledge_id


def list_knowledge(show_all: bool = False) -> list[Knowledge]:
    archive = archive_filter(show_all)
    with store.ensure() as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, created_at, archived_at FROM knowledge {archive} ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_knowledge(domain: str, show_all: bool = False) -> list[Knowledge]:
    archive = archive_filter(show_all, prefix="AND")

    if domain.endswith("/*"):
        domain_prefix = domain[:-2]
        where_clause = f"WHERE (domain = ? OR domain LIKE ?) {archive}"
        params = (domain_prefix, f"{domain_prefix}/%")
    else:
        where_clause = f"WHERE domain = ? {archive}"
        params = (domain,)

    with store.ensure() as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, created_at, archived_at FROM knowledge {where_clause} ORDER BY created_at DESC",
            params,
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def query_knowledge_by_agent(agent_id: str, show_all: bool = False) -> list[Knowledge]:
    archive = archive_filter(show_all, prefix="AND")
    with store.ensure() as conn:
        rows = conn.execute(
            f"SELECT knowledge_id, domain, agent_id, content, created_at, archived_at FROM knowledge WHERE agent_id = ? {archive} ORDER BY created_at DESC",
            (agent_id,),
        ).fetchall()
    return [_row_to_knowledge(row) for row in rows]


def get_knowledge(entry_id: str) -> Knowledge | None:
    with store.ensure() as conn:
        row = conn.execute(
            "SELECT knowledge_id, domain, agent_id, content, created_at, archived_at FROM knowledge WHERE knowledge_id = ?",
            (entry_id,),
        ).fetchone()
    return _row_to_knowledge(row) if row else None


def find_related_knowledge(
    entry: Knowledge, limit: int = 5, show_all: bool = False
) -> list[tuple[Knowledge, int]]:
    from space.lib.stopwords import extract_keywords

    keywords = extract_keywords(entry.content + " " + entry.domain)

    if not keywords:
        return []

    archive = archive_filter(show_all, prefix="AND")
    with store.ensure() as conn:
        try:
            conn.execute("CREATE TEMPORARY TABLE keywords (keyword TEXT)")
            conn.executemany("INSERT INTO keywords VALUES (?)", [(k,) for k in keywords])

            query = f"""
                SELECT k_entry.knowledge_id, k_entry.domain, k_entry.agent_id, k_entry.content,
                       k_entry.created_at, k_entry.archived_at, COUNT(kw.keyword) as score
                FROM knowledge k_entry, keywords kw
                WHERE k_entry.knowledge_id != ? AND
                      (k_entry.content LIKE '%' || kw.keyword || '%' OR k_entry.domain LIKE '%' || kw.keyword || '%')
                      {archive}
                GROUP BY k_entry.knowledge_id
                ORDER BY score DESC
                LIMIT ?
            """
            rows = conn.execute(query, (entry.knowledge_id, limit)).fetchall()
        finally:
            conn.execute("DROP TABLE IF EXISTS keywords")

    return [(_row_to_knowledge(row), row["score"]) for row in rows]


def archive_knowledge(entry_id: str, restore: bool = False) -> None:
    with store.ensure() as conn:
        if restore:
            cursor = conn.execute(
                "UPDATE knowledge SET archived_at = NULL WHERE knowledge_id = ?",
                (entry_id,),
            )
        else:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                "UPDATE knowledge SET archived_at = ? WHERE knowledge_id = ?",
                (now, entry_id),
            )
        if cursor.rowcount == 0:
            raise ValueError(f"Knowledge entry '{entry_id}' not found")


def get_domain_tree(parent_domain: str | None = None, show_all: bool = False) -> dict:
    from space.lib.uuid7 import short_id

    with store.ensure() as conn:
        if parent_domain:
            query = "SELECT domain, knowledge_id FROM knowledge WHERE domain LIKE ?"
            params = [f"{parent_domain}/%"]
            if not show_all:
                query += " AND archived_at IS NULL"
        else:
            query = "SELECT domain, knowledge_id FROM knowledge"
            params = []
            if not show_all:
                query += " WHERE archived_at IS NULL"

        query += " ORDER BY domain"
        rows = conn.execute(query, params).fetchall()

    tree: dict = {}
    for domain, knowledge_id in rows:
        parts = domain.split("/")
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current.setdefault(part, {"__ids": []})
                if "__ids" not in current[part]:
                    current[part]["__ids"] = []
                current[part]["__ids"].append(short_id(knowledge_id))
            else:
                current.setdefault(part, {})
                current = current[part]

    return tree


def count_knowledge() -> tuple[int, int, int]:
    with store.ensure() as conn:
        total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]
        archived = total - active
    return total, active, archived


def search(query: str, identity: str | None = None, all_agents: bool = False) -> list[SearchResult]:
    results = []

    agent_id = None
    if identity and not all_agents:
        agent = spawn.get_agent(identity)
        if not agent:
            raise ValueError(f"Agent '{identity}' not found")
        agent_id = agent.agent_id

    with store.ensure() as conn:
        sql_query = (
            "SELECT knowledge_id, domain, agent_id, content, created_at FROM knowledge "
            "WHERE (content LIKE ? OR domain LIKE ?) AND archived_at IS NULL"
        )
        params = [f"%{query}%", f"%{query}%"]

        if agent_id:
            sql_query += " AND agent_id = ?"
            params.append(agent_id)

        sql_query += " ORDER BY created_at ASC"
        rows = conn.execute(sql_query, params).fetchall()

        for row in rows:
            agent = spawn.get_agent(row["agent_id"])
            results.append(
                SearchResult(
                    source="knowledge",
                    reference=f"knowledge:{row['knowledge_id']}",
                    content=row["content"],
                    timestamp=row["created_at"],
                    agent_id=row["agent_id"],
                    identity=agent.identity if agent else row["agent_id"],
                    metadata={"knowledge_id": row["knowledge_id"], "domain": row["domain"]},
                )
            )
    return results


def stats() -> "KnowledgeStats":
    from space.core.models import KnowledgeStats

    total, active, archived = count_knowledge()
    with store.ensure() as conn:
        domains = conn.execute(
            "SELECT COUNT(DISTINCT domain) FROM knowledge WHERE archived_at IS NULL"
        ).fetchone()[0]

    return KnowledgeStats(
        available=True,
        total=total,
        active=active,
        archived=archived,
        topics=domains,
    )
