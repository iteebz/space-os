"""Task commands: CLI parsing & typer wiring."""

import contextlib
import os
import signal
import time

import typer

from space.os import config
from space.os.core.spawn.api import tasks
from space.os.models import TaskStatus

app = typer.Typer()


def list(
    status: str | None = None,
    role: str | None = None,
    all: bool = typer.Option(
        False, "--all", "-a", help="Show all tasks (including completed/failed)"
    ),
):
    """List tasks, optionally filtered by status and/or role.

    Default: Show pending and running tasks only.
    With --all/-a: Show all tasks including completed/failed/timeout.
    """
    if not all and status is None:
        status = "pending|running"

    if status and "|" in status:
        statuses = status.split("|")
        all_tasks = tasks.list_tasks(status=None, role=role)
        tasks_list = [t for t in all_tasks if t.status in statuses]
    else:
        tasks_list = tasks.list_tasks(status=status, role=role)

    if not tasks_list:
        typer.echo("No tasks.")
        return

    typer.echo(f"{'ID':<8} {'Identity':<12} {'Status':<12} {'Duration':<10} {'Created':<20}")
    typer.echo("-" * 70)

    durations = []
    for task in tasks_list:
        task_id = task.task_id[:8]
        ident = (task.agent_id or "unknown")[:11]
        stat = task.status
        dur = f"{task.duration:.1f}s" if task.duration else "-"
        created = task.created_at[:19] if task.created_at else "-"
        typer.echo(f"{task_id:<8} {ident:<12} {stat:<12} {dur:<10} {created:<20}")
        if task.duration:
            durations.append(task.duration)

    if durations:
        typer.echo("-" * 70)
        avg_dur = sum(durations) / len(durations)
        min_dur = min(durations)
        max_dur = max(durations)
        typer.echo(f"Avg: {avg_dur:.1f}s | Min: {min_dur:.1f}s | Max: {max_dur:.1f}s")


def logs(task_id: str):
    """Show full task details: input, output, stderr, timestamps, duration."""
    task = tasks.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)
    if not task.agent_id:
        typer.echo(f"❌ Task has invalid agent_id: {task_id}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\n📋 Task: {task.task_id}")
    typer.echo(f"Identity: {task.agent_id}")
    typer.echo(f"Status: {task.status}")

    if task.channel_id:
        typer.echo(f"Channel: {task.channel_id}")

    typer.echo(f"Created: {task.created_at}")
    if task.started_at:
        typer.echo(f"Started: {task.started_at}")
    if task.completed_at:
        typer.echo(f"Completed: {task.completed_at}")
    if task.duration is not None:
        typer.echo(f"Duration: {task.duration:.2f}s")

    typer.echo("\n--- Input ---")
    typer.echo(task.input)

    if task.output:
        typer.echo("\n--- Output ---")
        typer.echo(task.output)

    if task.stderr:
        typer.echo("\n--- Stderr ---")
        typer.echo(task.stderr)

    typer.echo()


def wait(task_id: str, timeout: float | None = None) -> int:
    """Block until task completes. Return exit code: 0=success, 1=failed, 124=timeout."""
    if timeout is None:
        timeout = config.load_config().get("timeouts", {}).get("task_wait", 300)

    task = tasks.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    start = time.time()
    while True:
        task = tasks.get_task(task_id)
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT):
            if task.status == TaskStatus.COMPLETED:
                return 0
            return 1

        if time.time() - start > timeout:
            tasks.update_task(
                task_id,
                status=TaskStatus.TIMEOUT,
                stderr="Wait timeout exceeded",
                mark_completed=True,
            )
            raise typer.Exit(124)

        time.sleep(0.1)


def kill(task_id: str):
    """Kill a running task."""
    task = tasks.get_task(task_id)
    if not task:
        typer.echo(f"❌ Task not found: {task_id}", err=True)
        raise typer.Exit(1)

    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT):
        typer.echo(f"⚠️ Task already {task.status}, nothing to kill")
        return

    if task.pid:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.kill(task.pid, signal.SIGTERM)

    tasks.update_task(task_id, status="failed", stderr="Killed by user", mark_completed=True)
    typer.echo(f"✓ Task {task_id[:8]} killed")


app.command()(list)
app.command()(logs)
app.command()(wait)
app.command()(kill)
