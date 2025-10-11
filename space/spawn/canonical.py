from . import registry


def set_canonical(agent_id: str, canonical_id: str):
    """Point agent_id to canonical_id."""
    with registry.get_db() as conn:
        conn.execute(
            "UPDATE agents SET canonical_id = ? WHERE id = ?",
            (canonical_id, agent_id),
        )
        conn.commit()


def get_canonical(agent_id: str) -> str:
    """Get canonical ID for agent, or agent_id if none set."""
    with registry.get_db() as conn:
        row = conn.execute("SELECT canonical_id FROM agents WHERE id = ?", (agent_id,)).fetchone()
        return row["canonical_id"] if row and row["canonical_id"] else agent_id


def add_alias(agent_id: str, alias: str):
    """Add alias for agent."""
    with registry.get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO agent_aliases (agent_id, alias) VALUES (?, ?)",
            (agent_id, alias),
        )
        conn.commit()


def get_aliases(agent_id: str) -> list[str]:
    """Get all aliases for agent."""
    with registry.get_db() as conn:
        rows = conn.execute(
            "SELECT alias FROM agent_aliases WHERE agent_id = ?", (agent_id,)
        ).fetchall()
        return [row["alias"] for row in rows]


def get_canonical_agents() -> list[dict]:
    """Get all canonical agents with their aliases."""
    with registry.get_db() as conn:
        canonical_agents = conn.execute(
            "SELECT id, name, self_description FROM agents WHERE canonical_id IS NULL"
        ).fetchall()

        result = []
        for agent in canonical_agents:
            agent_id = agent["id"]
            aliases = get_aliases(agent_id)

            pointing_to_me = conn.execute(
                "SELECT id FROM agents WHERE canonical_id = ?", (agent_id,)
            ).fetchall()

            result.append(
                {
                    "id": agent_id,
                    "name": agent["name"],
                    "self_description": agent["self_description"],
                    "aliases": aliases,
                    "linked_ids": [row["id"] for row in pointing_to_me],
                }
            )

        return result
