import sqlite3
import time

import typer

from space.os import events as events_lib
from space.os.lib import paths
from space.os.lib import stats as stats_lib
from space.os.spawn import registry

app = typer.Typer(invoke_without_command=True)


def _resolve_agent_id(fuzzy_match: str, include_archived: bool = False) -> tuple[str, str] | None:
    """Resolve agent ID from partial UUID or identity name. Returns (agent_id, display_name)."""
    registry.init_db()

    with registry.get_db() as conn:
        where_clause = "" if include_archived else "WHERE archived_at IS NULL"
        rows = conn.execute(f"SELECT id, name FROM agents {where_clause}").fetchall()

    candidates = []
    for row in rows:
        agent_id = row["id"]
        name = row["name"]

        if agent_id.startswith(fuzzy_match) or name and name.lower() == fuzzy_match.lower():
            candidates.append((agent_id, name))

    if len(candidates) == 1:
        agent_id, name = candidates[0]
        resolved = (
            registry.get_identity(name)
            if (name and len(name) == 36 and name.count("-") == 4)
            else name
        )
        return (agent_id, resolved or name or agent_id[:8])

    return None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Show archived agents"),
):
    if ctx.invoked_subcommand is None:
        list_agents(show_all=show_all)


@app.command("list")
def list_agents(show_all: bool = typer.Option(False, "--all", help="Show archived agents")):
    """List all agents (registered and orphaned across universe)."""

    stats = stats_lib.agent_stats(include_archived=show_all) or []

    if not stats:
        typer.echo("No agents found.")
        return

    registry.init_db()
    with registry.get_db() as conn:
        {row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM agents")}

    typer.echo(f"{'NAME':<20} {'ID':<10} {'E-S-B-M-K':<20} {'SELF'}")
    typer.echo("-" * 100)

    for s in sorted(stats, key=lambda a: a.agent_name):
        name = s.agent_name
        agent_id = s.agent_id
        short_id = agent_id[:8]

        if len(name) == 36 and name.count("-") == 4:
            resolved = registry.get_identity(name)
            if resolved:
                name = resolved

        desc = "-"
        esbmk = f"{s.events}-{s.spawns}-{s.msgs}-{s.mems}-{s.knowledge}"

        typer.echo(f"{name:<20} {short_id:<10} {esbmk:<20} {desc}")

    typer.echo()
    typer.echo(f"Total: {len(stats)}")


@app.command("inspect")
def inspect_agent(agent_ref: str):
    """Inspect agent activity and state."""
    result = _resolve_agent_id(agent_ref)

    if not result:
        typer.echo(f"Error: Agent not found for '{agent_ref}'")
        raise typer.Exit(1)

    agent_id, display_name = result
    short_id = agent_id[:8]

    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"Agent: {display_name} ({short_id})")
    typer.echo(f"{'─' * 60}\n")

    evts = events_lib.query(agent_id=agent_id, limit=50)

    if not evts:
        typer.echo("No activity recorded.")
        typer.echo()
        return

    event_types = {}
    for e in evts:
        et = e.event_type
        if et not in event_types:
            event_types[et] = 0
        event_types[et] += 1

    typer.echo("Activity summary:")
    for et, count in sorted(event_types.items(), key=lambda x: -x[1]):
        typer.echo(f"  {et}: {count}")
    typer.echo()

    typer.echo("Recent activity (last 10):")
    for e in reversed(evts[:10]):
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.timestamp))
        data_str = f" ({e.data[:50]})" if e.data else ""
        typer.echo(f"  [{ts}] {e.event_type}{data_str}")

    typer.echo(f"\n{'─' * 60}\n")


@app.command("merge")
def merge_agents(id_from: str, id_to: str):
    """Merge all data from one agent ID to another."""
    from_result = _resolve_agent_id(id_from)
    to_result = _resolve_agent_id(id_to)

    if not from_result:
        typer.echo(f"Error: Source agent '{id_from}' not found")
        raise typer.Exit(1)

    if not to_result:
        typer.echo(f"Error: Target agent '{id_to}' not found")
        raise typer.Exit(1)

    from_agent_id, from_display = from_result
    to_agent_id, to_display = to_result

    if from_agent_id == to_agent_id:
        typer.echo("Error: Cannot merge agent with itself")
        raise typer.Exit(1)

    typer.echo(f"Merging {from_display} → {to_display}")

    updated_count = 0

    with registry.get_db() as conn:
        updated_count += conn.execute(
            "UPDATE agents SET archived_at = ? WHERE id = ?", (int(time.time()), from_agent_id)
        ).rowcount
        conn.commit()

    dbs = {
        "events.db": [("events",)],
        "memory.db": [("memories",)],
        "knowledge.db": [("knowledge",)],
        "bridge.db": [("notes",), ("bookmarks",), ("messages",)],
    }

    counts = {}
    for db_name, tables in dbs.items():
        db_path = paths.dot_space() / db_name
        if db_path.exists():
            with sqlite3.connect(db_path) as conn:
                for (table,) in tables:
                    count = conn.execute(
                        f"UPDATE {table} SET agent_id = ? WHERE agent_id = ?",
                        (to_agent_id, from_agent_id),
                    ).rowcount
                    if count > 0:
                        counts[table] = count
                conn.commit()

    total = sum(counts.values())
    if counts:
        breakdown = ", ".join(f"{table}:{count}" for table, count in sorted(counts.items()))
        typer.echo(f"✓ Merged {total} records ({breakdown})")
    else:
        typer.echo("✓ Merged (no data to migrate)")
    events_lib.emit("agents", "merge", to_agent_id, f"merged {from_agent_id}")


@app.command("rename")
def rename_agent(agent_ref: str, new_name: str):
    """Rename an agent."""
    result = _resolve_agent_id(agent_ref)

    if not result:
        typer.echo(f"Error: Agent not found for '{agent_ref}'")
        raise typer.Exit(1)

    agent_id, _ = result

    registry.init_db()

    with registry.get_db() as conn:
        conn.execute("UPDATE agents SET name = ? WHERE id = ?", (new_name, agent_id))
        conn.commit()

    typer.echo(f"✓ Renamed to {new_name}")
    events_lib.emit("agents", "rename", agent_id, f"renamed to {new_name}")


@app.command("delete")
def delete_agent(
    agent_ref: str, force: bool = typer.Option(False, "--force", help="Skip confirmation")
):
    """Hard delete an agent and all related data. Use with caution - backups required."""
    result = _resolve_agent_id(agent_ref)

    if not result:
        typer.echo(f"Error: Agent not found for '{agent_ref}'")
        raise typer.Exit(1)

    agent_id, display_name = result

    if not force:
        typer.echo(f"⚠️  About to permanently delete: {display_name}")
        typer.echo("This will remove all data from:")
        typer.echo("  - agents table")
        typer.echo("  - memories table")
        typer.echo("  - events table")
        typer.echo("Ensure backups exist before proceeding.")
        if not typer.confirm("Continue?"):
            typer.echo("Cancelled.")
            return

    deleted_count = 0

    with registry.get_db() as conn:
        deleted_count += conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,)).rowcount
        conn.commit()

    memory_db_path = paths.dot_space() / "memory.db"
    if memory_db_path.exists():
        with sqlite3.connect(memory_db_path) as memory_conn:
            deleted_count += memory_conn.execute(
                "DELETE FROM memories WHERE agent_id = ?", (agent_id,)
            ).rowcount
            memory_conn.commit()

    events_db_path = paths.dot_space() / "events.db"
    if events_db_path.exists():
        with sqlite3.connect(events_db_path) as events_conn:
            deleted_count += events_conn.execute(
                "DELETE FROM events WHERE agent_id = ?", (agent_id,)
            ).rowcount
            events_conn.commit()

    typer.echo(f"✓ Deleted {display_name} ({deleted_count} records)")
    events_lib.emit("agents", "delete", agent_id, "permanently deleted")
