"""Spawn CLI: Agent Management & Task Orchestration."""

import contextlib
import json
import os
import signal
import sys
from typing import NoReturn

import typer

from space.cli import argv, output
from space.cli.errors import error_feedback
from space.core.models import SpawnStatus
from space.lib import paths, providers
from space.os.sessions.parsing import parse_jsonl_message
from space.os.spawn import api
from space.os.spawn.api import spawns
from space.os.spawn.formatting import (
    display_agent_trace,
    display_channel_trace,
    display_session_trace,
)
from space.workspace.stats import agent_stats

app = typer.Typer(invoke_without_command=True, add_completion=False, no_args_is_help=False)


def _find_session_file(spawn):
    """Find session file for spawn - check archive first, then discover from provider."""
    from datetime import datetime

    agent = api.get_agent(spawn.agent_id)
    if not agent:
        return None

    provider = agent.provider

    # Completed spawn: check archive
    if spawn.session_id:
        archive = paths.sessions_dir() / provider / f"{spawn.session_id}.jsonl"
        if archive.exists():
            return archive

    # Active spawn: discover from provider
    if spawn.status == "running":
        created_dt = datetime.fromisoformat(spawn.created_at.replace("Z", "+00:00"))
        created_ts = created_dt.timestamp()

        if provider == "claude":
            sessions_dir = providers.Claude.SESSIONS_DIR
            if sessions_dir.exists():
                # Find most recent session near spawn timestamp
                best_match = None
                best_time_diff = float("inf")

                for jsonl in sessions_dir.rglob("*.jsonl"):
                    try:
                        file_ctime = jsonl.stat().st_birthtime
                        time_diff = abs(file_ctime - created_ts)
                        if time_diff < 10 and time_diff < best_time_diff:  # Within 10 seconds
                            best_match = jsonl
                            best_time_diff = time_diff
                    except (OSError, AttributeError):
                        continue

                return best_match

    return None


def _display_session(session_file, tail_lines=0):
    """Display session content with optional tail."""
    from pathlib import Path

    if not Path(session_file).exists():
        typer.echo("⚠️  Session file not found")
        return

    lines = []
    with open(session_file) as f:
        for line in f:
            msg = parse_jsonl_message(line)
            if msg:
                lines.append(f"[{msg['role'].capitalize()}] {msg['text']}")

    if tail_lines > 0:
        lines = lines[-tail_lines:]

    for line in lines:
        typer.echo(line)


def _follow_session(session_file):
    """Follow active session file (tail -f style)."""
    import time
    from pathlib import Path

    path = Path(session_file)
    if not path.exists():
        typer.echo("⚠️  Session file not found")
        return

    typer.echo("\n🔄 Following session (Ctrl+C to stop)...\n")

    seen_lines = 0
    try:
        while True:
            with open(path) as f:
                lines = f.readlines()
                new_lines = lines[seen_lines:]

                for line in new_lines:
                    msg = parse_jsonl_message(line)
                    if msg:
                        typer.echo(f"[{msg['role'].capitalize()}] {msg['text']}")

                seen_lines = len(lines)

            time.sleep(1)
    except KeyboardInterrupt:
        typer.echo("\n\n✓ Stopped following")


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Constitutional identity registry. Register agents with constitution, spawn by identity, track execution."""
    output.init_context(ctx, json_output, quiet_output)

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        # Check if first arg is a known command name
        known_commands = {
            "register",
            "agents",
            "models",
            "inspect",
            "rename",
            "clone",
            "update",
            "merge",
            "list",
            "run",
            "cleanup",
            "health",
            "logs",
            "abort",
            "trace",
            "chain",
        }
        if (
            len(sys.argv) > 1
            and not sys.argv[1].startswith("-")
            and sys.argv[1] not in known_commands
        ):
            identity = sys.argv[1]
            agent = api.get_agent(identity)
            if agent:
                _dispatch_spawn(identity, sys.argv[2:], verbose=True)
                raise typer.Exit(0)
        typer.echo(ctx.get_help())


def _resolve_identity(stat_identity: str) -> str:
    """Resolve agent identity from stat record (may be UUID)."""
    name = stat_identity or ""
    if len(name) == 36 and name.count("-") == 4:
        agent = api.get_agent(name)
        if agent:
            return agent.identity
    return name


def _extract_resume_flag(args: list[str]) -> tuple[str | None, list[str]]:
    """Extract --resume/-r flag and optional value from args.

    Returns:
        (resume_value, remaining_args) where resume_value is None if --resume not present
    """
    return argv.extract_flag(args, "--resume", "-r")


def _dispatch_spawn(identity: str, args: list[str], verbose: bool = False):
    """Dispatch ephemeral spawn with task.

    Args:
        identity: Agent identity to spawn
        args: Command arguments (task required, may contain --resume flag)
        verbose: Show spawn progress messages

    Returns:
        Spawn object
    """
    resume, extra_args = _extract_resume_flag(args)
    if not extra_args:
        raise ValueError(
            f'Task required. Usage: {identity} "task description"\n'
            f'For coordination, use: bridge send <channel> "@{identity} task"'
        )
    if verbose:
        typer.echo(f"Spawning {identity}...\n")
    spawn = api.spawn_ephemeral(identity, " ".join(extra_args), channel_id=None, resume=resume)
    if verbose:
        typer.echo(f"\nSpawn ID: {spawn.id[:8]}")
        typer.echo(f"Track: spawn trace {spawn.id[:8]}")
    return spawn


@app.command()
@error_feedback
def agents(
    show_all: bool = typer.Option(False, "--all", help="Show archived agents"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """List registered and orphaned agents."""
    stats = agent_stats(show_all=show_all) or []

    if not stats:
        if json_output:
            typer.echo(json.dumps([]))
        else:
            typer.echo("No agents found.")
        return

    agents_data = []

    for s in stats:
        agent_id = s.agent_id
        if not agent_id:
            continue

        name = _resolve_identity(s.identity)
        agent = api.get_agent(agent_id)

        agents_data.append(
            {
                "identity": name,
                "agent_id": agent_id,
                "constitution": agent.constitution if agent and agent.constitution else "-",
                "model": agent.model if agent and agent.model else "-",
                "role": agent.role if agent and agent.role else "-",
            }
        )

    agents_data.sort(
        key=lambda d: (
            d["constitution"] == "-",
            d["constitution"] or "",
            d["identity"] or "",
        )
    )

    if json_output:
        typer.echo(json.dumps(agents_data))
    else:
        # Leading blank line for readability, similar to `spawn models`
        typer.echo()
        typer.echo(f"{'IDENTITY':<15} {'CONSTITUTION':<15} {'MODEL':<20} {'ROLE':<15}")
        for data in agents_data:
            typer.echo(
                f"{data['identity']:<15} {data['constitution']:<15} {data['model']:<20} {data['role']:<15}"
            )
        # Blank line before and after the total for a clear footer
        typer.echo()
        typer.echo(f"Total: {len(agents_data)}")
        typer.echo()


@app.command()
@error_feedback
def register(
    identity: str,
    model: str | None = typer.Option(
        None, "--model", "-m", help="Model ID. Run 'spawn models' to list available models"
    ),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename (e.g., zealot.md) - optional"
    ),
    role: str | None = typer.Option(
        None, "--role", "-r", help="Organizational role (e.g., executor, verifier, adversary)"
    ),
):
    """Register a new agent."""
    try:
        agent_id = api.register_agent(identity, model, constitution, role)
        typer.echo(f"✓ Registered {identity} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def models():
    """Show available LLM models."""
    first = True
    for prov in providers.PROVIDER_NAMES:
        provider_models = providers.MODELS.get(prov, [])
        if not provider_models:
            continue

        if not first:
            typer.echo()
        else:
            typer.echo()
        first = False

        if prov == "claude":
            header = "Claude Code"
        elif prov == "codex":
            header = "Codex CLI"
        elif prov == "gemini":
            header = "Gemini CLI"
        else:
            header = prov.capitalize()

        typer.echo(f"{header}:")
        for model in provider_models:
            mid = model["id"]
            desc = model.get("description") or ""
            tags = model.get("tags") or []
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            typer.echo(f"  - {mid:<26} {desc}{tag_str}")
    if not first:
        typer.echo()


@app.command()
@error_feedback
def clone(src: str, dst: str):
    """Copy agent with new identity."""
    try:
        agent_id = api.clone_agent(src, dst)
        typer.echo(f"✓ Cloned {src} → {dst} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def rename(old_name: str, new_name: str):
    """Change agent identity."""
    try:
        if api.rename_agent(old_name, new_name):
            typer.echo(f"✓ Renamed {old_name} → {new_name}")
        else:
            typer.echo(f"❌ Agent not found: {old_name}. Run `spawn` to list agents.", err=True)
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def update(
    identity: str,
    model: str | None = typer.Option(None, "--model", "-m", help="Full model name"),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename"
    ),
    role: str | None = typer.Option(None, "--role", "-r", help="Organizational role"),
):
    """Modify agent fields (constitution, model, role)."""
    try:
        api.update_agent(identity, constitution, model, role)
        typer.echo(f"✓ Updated {identity}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def inspect(identity: str):
    """View agent details and constitution."""
    from space.lib import paths

    agent = api.get_agent(identity)
    if not agent:
        typer.echo(f"❌ Agent not found: {identity}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nAgent: {agent.identity}")
    typer.echo(f"ID: {agent.agent_id}")
    typer.echo(f"Model: {agent.model}")
    typer.echo(f"Constitution: {agent.constitution or '-'}")
    typer.echo(f"Role: {agent.role or '-'}")
    typer.echo(f"Spawns: {agent.spawn_count}")
    typer.echo(f"Created: {agent.created_at}")
    typer.echo(f"Last Active: {agent.last_active_at or '-'}")

    if agent.constitution:
        const_path = paths.constitution(agent.constitution)
        if const_path.exists():
            typer.echo(f"\n--- {agent.constitution} ---")
            typer.echo(const_path.read_text())
        else:
            typer.echo(f"\n⚠️ Constitution file not found: {const_path}")
    typer.echo()


@app.command()
@error_feedback
def merge(id_from: str, id_to: str):
    """Consolidate data from one agent to another."""
    agent_from = api.get_agent(id_from)
    agent_to = api.get_agent(id_to)

    if not agent_from:
        typer.echo(f"Error: Agent '{id_from}' not found")
        raise typer.Exit(1)
    if not agent_to:
        typer.echo(f"Error: Agent '{id_to}' not found")
        raise typer.Exit(1)

    result = api.merge_agents(id_from, id_to)

    if not result:
        typer.echo("Error: Could not merge agents")
        raise typer.Exit(1)

    from_display = agent_from.identity or id_from[:8]
    to_display = agent_to.identity or id_to[:8]
    typer.echo(f"Merging {from_display} → {to_display}")
    typer.echo("✓ Merged")


@app.command(name="list")
def list_spawns(
    ctx: typer.Context,
    status: str | None = None,
    identity: str | None = None,
    all: bool = typer.Option(
        False, "--all", "-a", help="Show all spawns (including completed/failed)"
    ),
):
    """List spawns (filter by status/identity).

    Default: Show pending and running spawns only.
    With --all/-a: Show all spawns including completed/failed/timeout.
    """
    if not all and status is None:
        status = "pending|running"

    agent = None
    if identity:
        agent = api.get_agent(identity)
        if not agent:
            typer.echo(f"❌ Agent not found: {identity}", err=True)
            raise typer.Exit(1)

    if agent:
        all_spawns = spawns.get_spawns_for_agent(agent.agent_id)
    else:
        all_spawns = spawns.get_all_spawns()

    if status and "|" in status:
        statuses = status.split("|")
        spawns_list = [s for s in all_spawns if s.status in statuses]
    else:
        spawns_list = [s for s in all_spawns if status is None or s.status == status]

    if ctx.obj and ctx.obj.get("json_output"):
        data = [
            {
                "id": s.id,
                "agent_id": s.agent_id,
                "status": s.status,
                "session_id": s.session_id,
                "channel_id": s.channel_id,
                "created_at": s.created_at,
                "ended_at": s.ended_at,
            }
            for s in spawns_list
        ]
        typer.echo(json.dumps(data))
        return

    if not spawns_list:
        typer.echo("No spawns.")
        return

    typer.echo(f"{'ID':<8} {'Status':<12} {'Created':<20}")
    typer.echo("-" * 40)

    for spawn_obj in spawns_list:
        spawn_id = spawn_obj.id[:8]
        stat = spawn_obj.status
        created = spawn_obj.created_at[:19] if spawn_obj.created_at else "-"
        typer.echo(f"{spawn_id:<8} {stat:<12} {created:<20}")


@app.command()
@error_feedback
def logs(
    spawn_id: str,
    tail: int = typer.Option(0, "--tail", "-n", help="Show last N lines of session output"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow active session"),
):
    """Show spawn details and session output."""

    spawn_obj = spawns.get_spawn(spawn_id)
    if not spawn_obj:
        typer.echo(f"❌ Spawn not found: {spawn_id}", err=True)
        raise typer.Exit(1)
    if not spawn_obj.agent_id:
        typer.echo(f"❌ Spawn has invalid agent_id: {spawn_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n📋 Spawn: {spawn_obj.id}")
    typer.echo(f"Agent: {spawn_obj.agent_id}")
    typer.echo(f"Status: {spawn_obj.status}")

    if spawn_obj.channel_id:
        typer.echo(f"Channel: {spawn_obj.channel_id}")

    if spawn_obj.session_id:
        typer.echo(f"Session: {spawn_obj.session_id}")

    if spawn_obj.pid:
        typer.echo(f"PID: {spawn_obj.pid}")

    typer.echo(f"Created: {spawn_obj.created_at}")
    if spawn_obj.ended_at:
        typer.echo(f"Ended: {spawn_obj.ended_at}")
        try:
            from datetime import datetime

            start = datetime.fromisoformat(spawn_obj.created_at)
            end = datetime.fromisoformat(spawn_obj.ended_at)
            duration = (end - start).total_seconds()
            typer.echo(f"Duration: {duration:.1f}s")
        except (ValueError, TypeError):
            pass

    # Find session file
    session_file = _find_session_file(spawn_obj)
    if not session_file:
        typer.echo("\n⚠️  No session file found")
        return

    typer.echo(f"\n📄 Session: {session_file}")

    # Display session output
    if follow:
        _follow_session(session_file)
    else:
        _display_session(session_file, tail)


@app.command()
@error_feedback
def abort(spawn_id: str):
    """Abort running spawn - terminates task execution, agent identity preserved."""
    spawn_obj = spawns.get_spawn(spawn_id)
    if not spawn_obj:
        typer.echo(f"❌ Spawn not found: {spawn_id}", err=True)
        raise typer.Exit(1)

    if spawn_obj.status in (
        SpawnStatus.COMPLETED,
        SpawnStatus.FAILED,
        SpawnStatus.TIMEOUT,
        SpawnStatus.KILLED,
    ):
        typer.echo(f"⚠️ Spawn already {spawn_obj.status}, nothing to abort")
        return

    if spawn_obj.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(spawn_obj.pid, signal.SIGTERM)

    spawns.update_status(spawn_id, SpawnStatus.KILLED)
    typer.echo(f"✓ Spawn {spawn_id[:8]} aborted")


@app.command()
@error_feedback
def run(
    identity: str,
    instruction: str,
    channel: str | None = typer.Option(None, "--channel", "-c", help="Channel ID"),
    resume: str | None = typer.Option(None, "--resume", "-r", help="Session to resume"),
):
    """Run spawn directly (used by detached processes)."""
    try:
        spawn = api.spawn_ephemeral(identity, instruction, channel_id=channel, resume=resume)
        typer.echo(f"spawn:{spawn.id}")
    except Exception as e:
        typer.echo(f"error:{e}", err=True)
        raise typer.Exit(1) from e


@app.command()
@error_feedback
def cleanup():
    """Mark orphan spawns (dead PIDs) as failed."""
    count = spawns.cleanup_orphans()
    typer.echo(f"✓ Cleaned {count} orphan spawn(s)")


@app.command()
@error_feedback
def health():
    """Check for timed out or stalled spawns."""
    issues = spawns.detect_failures()

    total = sum(len(v) for v in issues.values())
    if total == 0:
        typer.echo("✓ All spawns healthy")
        return

    if issues["timeout"]:
        typer.echo(f"⚠️  Timed out ({spawns.SPAWN_TIMEOUT_MINUTES}m+):")
        for sid in issues["timeout"]:
            typer.echo(f"   {sid[:8]}")

    if issues["no_session"]:
        typer.echo(f"⚠️  No session file ({spawns.STALL_THRESHOLD_MINUTES}m+):")
        for sid in issues["no_session"]:
            typer.echo(f"   {sid[:8]}")

    if issues["stalled"]:
        typer.echo(f"⚠️  Stalled (no output {spawns.STALL_THRESHOLD_MINUTES}m+):")
        for sid in issues["stalled"]:
            typer.echo(f"   {sid[:8]}")

    typer.echo(f"\nTotal: {total} issue(s)")


@app.command()
@error_feedback
def chain(
    root_id: str = typer.Argument(
        None, help="Root spawn ID (shows subtree) or agent identity (shows all)"
    ),
):
    """Visualize spawn parent/child relationships as tree.

    If SPAWN_ID is a partial/full spawn ID: show tree rooted at that spawn.
    If SPAWN_ID is an agent identity: show all spawn chains for that agent.
    Omit SPAWN_ID: show top-level spawns (those without parents).
    """
    from datetime import datetime

    agent_cache: dict[str, str] = {}

    def _agent_display(agent_id: str | None) -> str:
        if not agent_id:
            return "-"
        if agent_id in agent_cache:
            return agent_cache[agent_id]

        agent_obj = api.get_agent(agent_id)
        display = agent_obj.identity if agent_obj and agent_obj.identity else agent_id[:8]
        agent_cache[agent_id] = display
        return display

    def _format_row(spawn, prefix="", connector="") -> str:
        import logging

        status_symbol = {
            "pending": "⧗",
            "running": "⚡",
            "completed": "✓",
            "failed": "✗",
            "timeout": "⏱",
            "paused": "⏸",
            "killed": "⚠",
        }.get(spawn.status, "?")

        try:
            created = datetime.fromisoformat(spawn.created_at).strftime("%H:%M:%S")
        except (ValueError, TypeError, AttributeError):
            logging.getLogger(__name__).warning(
                f"Malformed timestamp for spawn {spawn.id}: {spawn.created_at}"
            )
            created = "-"

        return (
            f"{prefix}{connector}{status_symbol} "
            f"{spawn.id[:8]:<8} | {_agent_display(spawn.agent_id):<12} | {spawn.status:<10} | {created}"
        )

    def _render_tree(spawn_obj, prefix="", is_last=True, visited: set[str] | None = None):
        if visited is None:
            visited = set()
        if spawn_obj.id in visited:
            typer.echo(prefix + ("└── " if is_last else "├── ") + "↻ cycle detected")
            return
        visited.add(spawn_obj.id)

        connector = "└── " if is_last else "├── "
        typer.echo(_format_row(spawn_obj, prefix, connector))

        children = spawns.get_spawn_children(spawn_obj.id)
        for idx, child in enumerate(children):
            child_prefix = prefix + ("    " if is_last else "│   ")
            _render_tree(child, child_prefix, idx == len(children) - 1, visited)

    if root_id is None:
        roots = spawns.get_all_root_spawns(limit=200)
        if len(roots) >= 200:
            typer.echo(
                "⚠️  Truncated: showing first 200 roots (use spawn chain <spawn_id> for specific tree)"
            )
        typer.echo("")
    else:
        agent = api.get_agent(root_id)
        if agent:
            roots = spawns.get_root_spawns_for_agent(agent.agent_id, limit=500)
            if len(roots) >= 500:
                typer.echo("⚠️  Truncated: showing first 500 roots for this agent")
                typer.echo("")
        else:
            spawn_obj = spawns.get_spawn(root_id)
            if not spawn_obj:
                typer.echo(f"❌ Spawn or agent not found: {root_id}", err=True)
                raise typer.Exit(1)
            roots = [spawn_obj]

    if not roots:
        typer.echo("No spawns found.")
        return

    typer.echo(f"{'STATE':<5} {'ID':<10} | {'AGENT':<12} | {'STATUS':<12} | {'CREATED':<10}")
    typer.echo("-" * 70)

    for idx, root in enumerate(roots):
        _render_tree(root, "", idx == len(roots) - 1)


@app.command()
@error_feedback
def trace(query: str = typer.Argument(None)):
    """Trace execution: agent spawns, session context, or channel activity.

    Query syntax:
    - Explicit: agent:zealot, session:7a6a07de, channel:general (recommended)
    - Implicit: zealot, 7a6a07de, general (auto-inferred)
    """
    if query is None:
        typer.echo("Usage: spawn trace [QUERY]")
        typer.echo("Query syntax:")
        typer.echo("  - Explicit: agent:zealot, session:7a6a07de, channel:general")
        typer.echo("  - Implicit: zealot, 7a6a07de, general (auto-inferred)")
        raise typer.Exit(0)

    try:
        result = api.trace_query(query)
    except ValueError as e:
        typer.echo(f"✗ {e}", err=True)
        raise typer.Exit(1) from e

    if result["type"] == "identity":
        display_agent_trace(result)
    elif result["type"] == "session":
        display_session_trace(result)
    elif result["type"] == "channel":
        display_channel_trace(result)


def dispatch_agent_from_name() -> NoReturn:
    """Entry point: route command name (argv[0]) to agent if registered."""
    prog_name = sys.argv[0].split("/")[-1]

    agent = api.get_agent(prog_name)
    if not agent:
        typer.echo(f"Error: '{prog_name}' is not a registered agent identity.", err=True)
        typer.echo("Run 'spawn agents' to list available agents.", err=True)
        sys.exit(1)

    args = sys.argv[1:] if len(sys.argv) > 1 else []
    _dispatch_spawn(agent.identity, args)
    sys.exit(0)


def main() -> None:
    """Entry point for spawn command."""
    try:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            potential_identity = sys.argv[1]
            agent = api.get_agent(potential_identity)
            if agent:
                _dispatch_spawn(potential_identity, sys.argv[2:], verbose=True)
                return
            # Check if it looks like an identity (not a subcommand)
            known_commands = {
                "agents",
                "register",
                "models",
                "clone",
                "rename",
                "update",
                "inspect",
                "merge",
                "list",
                "run",
                "cleanup",
                "health",
                "logs",
                "abort",
                "trace",
                "chain",
            }
            if potential_identity not in known_commands:
                typer.echo(
                    f"Agent '{potential_identity}' not found. Register with: spawn register {potential_identity} --model <model>",
                    err=True,
                )
                typer.echo(
                    "Run 'spawn agents' to list registered agents or 'spawn --help' for commands.",
                    err=True,
                )
                raise typer.Exit(1)
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main", "dispatch_agent_from_name"]
