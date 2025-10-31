"""Daemon commands: spawn and manage autonomous swarms."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import typer

from . import api

app = typer.Typer(invoke_without_command=True)

DAEMON_TASKS = [
    ("upkeep", "Repository hygiene, memory compaction, artifact checksumming"),
    ("sync_chats", "Discover and sync chats from claude/codex/gemini providers"),
]


def _run_all_daemons(role: str = "zealot") -> None:
    """Run all configured daemons in parallel."""
    typer.echo("🔄 Space health heartbeat: running daemons in parallel\n")

    def spawn_daemon(daemon_type: str, description: str) -> tuple[str, str, str]:
        """Spawn a single daemon and return (daemon_type, task_id, status)."""
        try:
            task_id = api.create_daemon_task(daemon_type, role=role)
            return (daemon_type, task_id, "spawned")
        except Exception as e:
            return (daemon_type, "", f"error: {e}")

    results = []
    with ThreadPoolExecutor(max_workers=len(DAEMON_TASKS)) as executor:
        futures = {
            executor.submit(spawn_daemon, daemon_type, desc): (daemon_type, desc)
            for daemon_type, desc in DAEMON_TASKS
        }
        for future in as_completed(futures):
            daemon_type, description = futures[future]
            try:
                daemon_type_res, task_id, status = future.result()
                results.append((daemon_type_res, description, task_id, status))
            except Exception as e:
                results.append((daemon_type, description, "", f"error: {e}"))

    results.sort(key=lambda x: x[0])
    typer.echo(f"{'Daemon':<15} {'Status':<12} {'Task ID':<10} Description")
    typer.echo("-" * 80)
    for daemon_type, description, task_id, status in results:
        task_display = task_id[:8] if task_id else "-"
        status_icon = "✓" if status == "spawned" else "❌"
        typer.echo(f"{daemon_type:<15} {status_icon} {status:<10} {task_display:<10} {description}")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Space health heartbeat: run all daemons in parallel, or invoke subcommands."""
    if ctx.invoked_subcommand is None:
        # Retrieve identity from ctx.obj
        role = ctx.obj.get("identity", "zealot")  # Default to zealot if not provided
        _run_all_daemons(role=role)


@app.command("upkeep")
def upkeep(
    ctx: typer.Context,
    wait_for_completion: bool = typer.Option(
        False, "--wait", "-w", help="Block until task completes"
    ),
):
    """Spawn upkeep daemon: repository hygiene, memory compaction, artifact checksumming."""
    role = ctx.obj.get("identity", "zealot")
    try:
        task_id = api.create_daemon_task("upkeep", role=role)
        typer.echo(f"✓ Daemon spawned: {task_id[:8]}")

        if wait_for_completion:
            task = api.get_daemon_task(task_id)
            if task:
                typer.echo(f"  Status: {task.status}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command("status")
def status(
    all_tasks: bool = typer.Option(False, "--all", "-a", help="Show all tasks including completed"),
):
    """Show daemon task status."""
    filter_status = None if all_tasks else "pending|running"
    daemon_tasks = api.list_daemon_tasks(status=filter_status)

    if not daemon_tasks:
        typer.echo("No active daemon tasks")
        return

    typer.echo(f"{'ID':<8} {'Role':<12} {'Status':<12} {'Input':<30}")
    typer.echo("-" * 70)

    for task in daemon_tasks:
        task_id = task.task_id[:8]
        role = (task.agent_id or "unknown")[:11]
        stat = task.status
        task_input = (task.input or "")[:29]
        typer.echo(f"{task_id:<8} {role:<12} {stat:<12} {task_input:<30}")
