"""Daemon commands: spawn and manage autonomous swarms."""

import typer

from . import api

app = typer.Typer()


@app.command()
def upkeep(
    role: str = typer.Option("zealot", "--as", help="Constitutional identity to run daemon"),
    wait_for_completion: bool = typer.Option(False, "--wait", "-w", help="Block until task completes"),
):
    """Spawn upkeep daemon: repository hygiene, memory compaction, artifact checksumming."""
    try:
        task_id = api.create_daemon_task("upkeep", role=role)
        typer.echo(f"✓ Daemon spawned: {task_id[:8]}")
        
        if wait_for_completion:
            task = api.get_daemon_task(task_id)
            if task:
                typer.echo(f"  Status: {task.status}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)


@app.command()
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
