"""Spawn task management commands: tasks, logs, wait, kill."""

import time
import signal
import os
import typer
from .. import registry


def tasks_cmd(status: str | None = None, identity: str | None = None):
    """List tasks, optionally filtered by status and/or identity."""
    tasks = registry.list_tasks(status=status, identity=identity)
    
    if not tasks:
        typer.echo("No tasks.")
        return
    
    typer.echo(f"{'ID':<8} {'Identity':<12} {'Status':<12} {'Duration':<10} {'Created':<20}")
    typer.echo("-" * 70)
    
    for task in tasks:
        task_id = task["id"][:8]
        ident = task["identity"][:11]
        stat = task["status"]
        dur = f"{task['duration']:.1f}s" if task["duration"] else "-"
        created = task["created_at"][:19] if task["created_at"] else "-"
        typer.echo(f"{task_id:<8} {ident:<12} {stat:<12} {dur:<10} {created:<20}")


def logs_cmd(task_id: str):
    """Show full task details: input, output, stderr, timestamps, duration."""
    task = registry.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"\n📋 Task: {task['id']}")
    typer.echo(f"Identity: {task['identity']}")
    typer.echo(f"Status: {task['status']}")
    
    if task["channel_id"]:
        typer.echo(f"Channel: {task['channel_id']}")
    
    typer.echo(f"Created: {task['created_at']}")
    if task["started_at"]:
        typer.echo(f"Started: {task['started_at']}")
    if task["completed_at"]:
        typer.echo(f"Completed: {task['completed_at']}")
    if task["duration"] is not None:
        typer.echo(f"Duration: {task['duration']:.2f}s")
    
    typer.echo("\n--- Input ---")
    typer.echo(task["input"])
    
    if task["output"]:
        typer.echo("\n--- Output ---")
        typer.echo(task["output"])
    
    if task["stderr"]:
        typer.echo("\n--- Stderr ---")
        typer.echo(task["stderr"])
    
    typer.echo()


def wait_cmd(task_id: str, timeout: float = 300.0) -> int:
    """Block until task completes. Return exit code: 0=success, 1=failed, 124=timeout."""
    task = registry.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)
    
    start = time.time()
    while True:
        task = registry.get_task(task_id)
        if task["status"] in ("completed", "failed", "timeout"):
            if task["status"] == "completed":
                return 0
            else:
                return 1
        
        if time.time() - start > timeout:
            registry.update_task(task_id, status="timeout", stderr="Wait timeout exceeded", completed_at=True)
            raise typer.Exit(124)
        
        time.sleep(0.1)


def kill_cmd(task_id: str):
    """Kill a running task."""
    task = registry.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)
    
    if task["status"] in ("completed", "failed", "timeout"):
        typer.echo(f"⚠️ Task already {task['status']}, nothing to kill")
        return
    
    if task["pid"]:
        try:
            os.kill(task["pid"], signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    
    registry.update_task(task_id, status="failed", stderr="Killed by user", completed_at=True)
    typer.echo(f"✓ Task {task_id[:8]} killed")
