import json
import time

import typer

from space.apps import stats as stats_lib
from space.os import config, db
from space.os import events as events_lib
from space.os.lib import errors, paths

from . import db as spawn_db
from . import spawn as spawn_module
from . import tasks

errors.install_error_handler("spawn")

spawn = typer.Typer()


@spawn.callback()
def cb(ctx: typer.Context):
    """Constitutional agent registry"""
    pass


@spawn.command(
    name="launch",
    hidden=True,
    context_settings={"allow_extra_args": True, "allow_interspersed_args": False},
)
def launch(ctx: typer.Context, agent_id: str):
    """Launch an agent (internal fallback)."""
    _spawn_from_registry(agent_id, ctx.args)


spawn.command(name="tasks")(tasks.tasks)
spawn.command(name="logs")(tasks.logs)
spawn.command(name="wait")(tasks.wait)
spawn.command(name="kill")(tasks.kill)
spawn.command(name="rename")(tasks.rename)


def _resolve_agent_id(fuzzy_match: str, include_archived: bool = False) -> tuple[str, str] | None:
    """Resolve agent ID from partial UUID or identity name. Returns (agent_id, display_name)."""
    with spawn_db.connect() as conn:
        where_clause = "" if include_archived else "WHERE archived_at IS NULL"
        rows = conn.execute(f"SELECT agent_id, name FROM agents {where_clause}").fetchall()

    candidates = []
    for row in rows:
        agent_id = row["agent_id"]
        name = row["name"]

        if agent_id.startswith(fuzzy_match) or name and name.lower() == fuzzy_match.lower():
            candidates.append((agent_id, name))

    if len(candidates) == 1:
        agent_id, name = candidates[0]
        resolved = (
            spawn_db.get_agent_name(name)
            if (name and len(name) == 36 and name.count("-") == 4)
            else name
        )
        return (agent_id, resolved or name or agent_id[:8])

    return None


@spawn.command("agents")
def list_agents(show_all: bool = typer.Option(False, "--all", help="Show archived agents")):
    """List all agents (registered and orphaned across universe)."""
    stats = stats_lib.agent_stats(include_archived=show_all) or []

    if not stats:
        typer.echo("No agents found.")
        return

    with spawn_db.connect() as conn:
        {row["agent_id"]: row["name"] for row in conn.execute("SELECT agent_id, name FROM agents")}

    typer.echo(f"{'NAME':<20} {'ID':<10} {'E-S-B-M-K':<20} {'POLLS':<30}")
    typer.echo("-" * 100)

    for s in sorted(stats, key=lambda a: a.agent_name):
        name = s.agent_name
        agent_id = s.agent_id
        short_id = agent_id[:8]

        if len(name) == 36 and name.count("-") == 4:
            resolved = spawn_db.get_agent_name(name)
            if resolved:
                name = resolved

        esbmk = f"{s.events}-{s.spawns}-{s.msgs}-{s.mems}-{s.knowledge}"

        polls_str = "-"
        if s.active_polls:
            polls_str = "🔴 " + ", ".join(s.active_polls)

        typer.echo(f"{name:<20} {short_id:<10} {esbmk:<20} {polls_str}")

    typer.echo()
    typer.echo(f"Total: {len(stats)}")


@spawn.command("registry")
def show_registry():
    """Show constitutional registry: constitutional evolution provenance.

    The registry tracks all constitutional versions by hash, enabling complete
    provenance of agent personality and instruction changes over time. Each
    constitution is content-addressable via its hash, creating an immutable
    audit trail of constitutional evolution.
    """
    with spawn_db.connect() as conn:
        rows = conn.execute(
            "SELECT hash, content, created_at FROM constitutions ORDER BY created_at DESC"
        ).fetchall()

        if not rows:
            typer.echo("Registry empty.")
            return

        typer.echo("CONSTITUTIONAL REGISTRY - Provenance of Agent Personality Evolution")
        typer.echo("=" * 80)
        typer.echo()

        for row in rows:
            hash_val = row["hash"]
            content = row["content"]
            created = row["created_at"]

            lines = content.split("\n")
            first_line = lines[0][:60] if lines else "(empty)"
            line_count = len(lines)

            typer.echo(f"Hash:     {hash_val}")
            typer.echo(f"Created:  {created}")
            typer.echo(f"Lines:    {line_count}")
            typer.echo(f"Preview:  {first_line}")
            typer.echo()


@spawn.command("backfill")
def backfill():
    """Backfill orphaned agent IDs from bridge into spawn_db."""
    count = spawn_db.backfill_unknown_agents()
    if count > 0:
        typer.echo(f"Registered {count} orphaned agent(s)")
    else:
        typer.echo("No orphaned agents found")


@spawn.command("describe")
def describe(
    identity: str = typer.Option(..., "--as", help="Identity to describe"),
    description: str = typer.Argument(None, help="Description to set"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """Get or set self-description for an identity."""
    if description:
        updated = spawn_db.set_self_description(identity, description)
        if json_output:
            typer.echo(
                json.dumps({"identity": identity, "description": description, "updated": updated})
            )
        elif updated:
            typer.echo(f"{identity}: {description}")
        else:
            typer.echo(f"No agent: {identity}")
    else:
        desc = spawn_db.get_self_description(identity)
        if json_output:
            typer.echo(json.dumps({"identity": identity, "description": desc}))
        elif desc:
            typer.echo(desc)
        else:
            typer.echo(f"No self-description for {identity}")


@spawn.command("inspect")
def inspect(agent_ref: str):
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


@spawn.command("merge")
def merge(id_from: str, id_to: str):
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

    with spawn_db.connect() as conn:
        updated_count += conn.execute(
            "UPDATE agents SET archived_at = ? WHERE agent_id = ?",
            (int(time.time()), from_agent_id),
        ).rowcount

    dbs = {
        "events.db": [("events",)],
        "memory.db": [("memories",)],
        "knowledge.db": [("knowledge",)],
        "bridge.db": [("notes",), ("bookmarks",), ("messages",)],
    }

    counts = {}
    db_names_map = {
        "events.db": "events",
        "memory.db": "memory",
        "knowledge.db": "knowledge",
        "bridge.db": "bridge",
    }
    for db_name, tables in dbs.items():
        db_path = paths.space_data() / db_name
        if db_path.exists():
            registry_name = db_names_map.get(db_name)
            if registry_name:
                with db.ensure(registry_name) as conn:
                    for (table,) in tables:
                        count = conn.execute(
                            f"UPDATE {table} SET agent_id = ? WHERE agent_id = ?",
                            (to_agent_id, from_agent_id),
                        ).rowcount
                        if count > 0:
                            counts[table] = count

    total = sum(counts.values())
    if counts:
        breakdown = ", ".join(f"{table}:{count}" for table, count in sorted(counts.items()))
        typer.echo(f"✓ Merged {total} records ({breakdown})")
    else:
        typer.echo("✓ Merged (no data to migrate)")
    events_lib.emit("agents", "merge", to_agent_id, f"merged {from_agent_id}")


@spawn.command("delete")
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

    with spawn_db.connect() as conn:
        deleted_count += conn.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,)).rowcount

    memory_db_path = paths.space_data() / "memory.db"
    if memory_db_path.exists():
        with db.ensure("memory") as memory_conn:
            deleted_count += memory_conn.execute(
                "DELETE FROM memories WHERE agent_id = ?", (agent_id,)
            ).rowcount

    events_db_path = paths.space_data() / "events.db"
    if events_db_path.exists():
        with db.ensure("events") as events_conn:
            deleted_count += events_conn.execute(
                "DELETE FROM events WHERE agent_id = ?", (agent_id,)
            ).rowcount

    typer.echo(f"✓ Deleted {display_name} ({deleted_count} records)")
    events_lib.emit("agents", "delete", agent_id, "permanently deleted")


def _spawn_from_registry(arg: str, extra_args: list[str]):
    """Launch agent by role or agent_name."""
    agent = None
    model = None
    context = None
    passthrough = []
    task = None

    i = 0
    while i < len(extra_args):
        if extra_args[i] == "--as" and i + 1 < len(extra_args):
            agent = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--model" and i + 1 < len(extra_args):
            model = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--channel" and i + 1 < len(extra_args):
            extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--context" and i + 1 < len(extra_args):
            context = extra_args[i + 1]
            i += 2
        elif extra_args[i] == "--sonnet":
            model = spawn_module.resolve_model_alias("sonnet")
            i += 1
        elif extra_args[i] == "--haiku":
            model = spawn_module.resolve_model_alias("haiku")
            i += 1
        elif not task and not extra_args[i].startswith("-"):
            task = extra_args[i]
            i += 1
        else:
            passthrough.append(extra_args[i])
            i += 1

    config.init_config()
    cfg = config.load_config()

    if arg in cfg["roles"]:
        if task:
            agent_obj = _get_agent(arg, agent, model, cfg)
            full_prompt = (context + "\n\n" + task) if context else task
            result = agent_obj.run(full_prompt)
            typer.echo(result)
        else:
            spawn_module.launch_agent(
                arg, role=arg, base_agent=agent, extra_args=passthrough, model=model
            )
        return

    if "-" in arg:
        inferred_role = arg.split("-", 1)[0]
        if inferred_role in cfg["roles"]:
            if task:
                agent_obj = _get_agent(arg, agent, model, cfg)
                full_prompt = (context + "\n\n" + task) if context else task
                result = agent_obj.run(full_prompt)
                typer.echo(result)
            else:
                spawn_module.launch_agent(
                    inferred_role,
                    role=arg,
                    base_agent=agent,
                    extra_args=passthrough,
                    model=model,
                )
            return

    typer.echo(f"❌ Unknown role or agent: {arg}", err=True)
    raise typer.Exit(1)


def _get_agent(role: str, base_agent: str | None, model: str | None, cfg: dict):
    """Get agent instance by role."""
    from space.os.lib import agents

    actual_role = role
    if actual_role not in cfg["roles"]:
        typer.echo(f"❌ Unknown role: {actual_role}", err=True)
        raise typer.Exit(1)

    role_cfg = cfg["roles"][actual_role]
    actual_base_agent = base_agent or role_cfg["base_agent"]

    agent_cfg = cfg.get("agents", {}).get(actual_base_agent)
    if not agent_cfg:
        typer.echo(f"❌ Unknown agent: {actual_base_agent}", err=True)
        raise typer.Exit(1)

    command = agent_cfg.get("command")
    agent_map = {
        "claude": agents.claude,
        "gemini": agents.gemini,
        "codex": agents.codex,
    }

    if command not in agent_map:
        typer.echo(f"❌ Unknown agent command: {command}", err=True)
        raise typer.Exit(1)

    agent_module = agent_map[command]
    return _AgentRunner(actual_identity, agent_module)


class _AgentRunner:
    """Simple agent runner wrapper."""

    def __init__(self, identity: str, agent_module):
        self.identity = identity
        self.agent_module = agent_module

    def run(self, prompt: str | None = None) -> str:
        return self.agent_module.spawn(self.identity, prompt)


def main() -> None:
    """Entry point for poetry script."""
    import sys

    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        cmd = sys.argv[1]
        if cmd not in [
            "rename",
            "tasks",
            "logs",
            "wait",
            "kill",
            "agents",
            "registry",
            "describe",
            "inspect",
            "merge",
            "delete",
            "backfill",
        ]:
            sys.argv.insert(1, "launch")

    spawn()


if __name__ == "__main__":
    main()
