"""Query builder helpers to DRY up common SQL patterns."""

import sqlite3
from typing import Any


def agent_by_name(conn: sqlite3.Connection, name: str, include_archived: bool = False) -> list[str]:
    """Get agent UUIDs by name. Returns list of agent_ids."""
    archive_filter = "" if include_archived else "AND archived_at IS NULL"
    rows = conn.execute(
        f"SELECT agent_id FROM agents WHERE name = ? {archive_filter}", (name,)
    ).fetchall()
    return [row["agent_id"] for row in rows]


def agent_by_id(conn: sqlite3.Connection, agent_id: str) -> str | None:
    """Get agent name by UUID."""
    row = conn.execute("SELECT name FROM agents WHERE agent_id = ?", (agent_id,)).fetchone()
    return row["name"] if row else None


def count_table(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    """Count total records in table with optional WHERE clause."""
    query = f"SELECT COUNT(*) FROM {table}"
    if where:
        query += f" WHERE {where}"
    return conn.execute(query).fetchone()[0]


def count_active(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    """Count active (non-archived) records."""
    conditions = ["archived_at IS NULL"]
    if where:
        conditions.append(where)
    return count_table(conn, table, " AND ".join(conditions))


def count_archived(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    """Count archived records."""
    conditions = ["archived_at IS NOT NULL"]
    if where:
        conditions.append(where)
    return count_table(conn, table, " AND ".join(conditions))


def select_with_filter(
    conn: sqlite3.Connection,
    table: str,
    columns: str = "*",
    where: str = "",
    order_by: str = "",
    limit: int | None = None,
    include_archived: bool = False,
) -> list[sqlite3.Row]:
    """Build SELECT with archive filter, WHERE, ORDER BY, and LIMIT."""
    query = f"SELECT {columns} FROM {table}"

    conditions = []
    if not include_archived:
        conditions.append("archived_at IS NULL")
    if where:
        conditions.append(where)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if order_by:
        query += f" {order_by}"

    if limit:
        query += f" LIMIT {limit}"

    return conn.execute(query).fetchall()


def select_distinct(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    where: str = "",
    params: tuple = (),
    include_archived: bool = False,
) -> list[str]:
    """Get distinct values from column with optional filter."""
    query = f"SELECT DISTINCT {column} FROM {table}"

    conditions = []
    if not include_archived:
        conditions.append("archived_at IS NULL")
    if where:
        conditions.append(where)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    rows = conn.execute(query, params).fetchall()
    return [row[0] for row in rows]


def count_by_group(
    conn: sqlite3.Connection,
    table: str,
    group_column: str,
    where: str = "",
    order_by: str = "count DESC",
    limit: int | None = None,
) -> list[tuple[str, int]]:
    """GROUP BY with COUNT(*). Returns [(group_value, count), ...]."""
    query = f"SELECT {group_column}, COUNT(*) as count FROM {table}"

    if where:
        query += f" WHERE {where}"

    query += f" GROUP BY {group_column}"

    if order_by:
        query += f" ORDER BY {order_by}"

    params = ()
    if limit:
        query += " LIMIT ?"
        params = (limit,)

    rows = conn.execute(query, params).fetchall()
    return [(row[0], row[1]) for row in rows]


def update_where(
    conn: sqlite3.Connection, table: str, updates: dict[str, Any], where: str, params: tuple
) -> None:
    """Execute UPDATE with safe parameterization.

    Args:
        conn: Database connection
        table: Table name
        updates: Dict of {column: value} to update
        where: WHERE clause (e.g. "agent_id = ?")
        params: Tuple of params (values + where_params in order)
    """
    if not updates:
        return

    set_clause = ", ".join([f"{col} = ?" for col in updates])
    query = f"UPDATE {table} SET {set_clause} WHERE {where}"

    all_params = tuple(updates.values()) + params
    conn.execute(query, all_params)


def delete_where(conn: sqlite3.Connection, table: str, where: str, params: tuple) -> None:
    """Execute DELETE with safe parameterization."""
    query = f"DELETE FROM {table} WHERE {where}"
    conn.execute(query, params)
