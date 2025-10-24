import json
from datetime import datetime

import typer

from space.os.spawn import db as spawn_db

app = typer.Typer()


@app.command()
def list(
    status: str = typer.Option(
        None, "--status", help="Filter by status (pending, running, completed, failed, timeout)"
    ),
    identity: str = typer.Option(None, "--identity", help="Filter by agent identity"),
    channel: str = typer.Option(None, "--channel", help="Filter by channel name"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output"),
):
    """List all tasks."""
    from space.os.bridge import api

    try:
        tasks = spawn_db.list_tasks(status=status, identity=identity)

        if channel:
            channel_id = api.resolve_channel_id(channel)
            tasks = [t for t in tasks if t.get("channel_id") == channel_id]

        if not tasks:
            if not quiet_output:
                typer.echo("No tasks found.")
            return

        if json_output:
            typer.echo(json.dumps(tasks, indent=2, default=str))
        elif not quiet_output:
            typer.echo("TASKS:")
            for row in tasks:
                task_id = row["task_id"][-8:]
                task_status = row["status"]
                agent_id = row["agent_id"]
                agent_name = spawn_db.get_identity(agent_id) or agent_id
                created = row["created_at"]
                duration = ""
                if row["started_at"] and row["completed_at"]:
                    dt = datetime.fromisoformat(row["completed_at"]) - datetime.fromisoformat(
                        row["started_at"]
                    )
                    duration = f" ({int(dt.total_seconds())}s)"
                typer.echo(f"  [{task_id}] {task_status:10} {agent_name:15} {created}{duration}")
    except Exception as exc:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        elif not quiet_output:
            typer.echo(f"❌ {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def logs(
    task_id: str = typer.Argument(..., help="Task UUID (full or 8-char suffix)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """Show task input, output, and stderr."""
    try:
        task = spawn_db.get_task(task_id)
        if not task:
            tasks = spawn_db.list_tasks()
            task = next((t for t in tasks if t["task_id"].endswith(task_id)), None)

        if not task:
            typer.echo(f"❌ Task not found: {task_id}", err=True)
            raise typer.Exit(code=1)

        if json_output:
            typer.echo(json.dumps(task, indent=2, default=str))
        else:
            agent_name = spawn_db.get_identity(task["agent_id"]) or task["agent_id"]
            typer.echo(f"Task: {task['task_id'][-8:]}")
            typer.echo(f"Status: {task['status']}")
            typer.echo(f"Agent: {agent_name}")
            typer.echo()
            if task["input"]:
                typer.echo("INPUT:")
                typer.echo(task["input"])
                typer.echo()
            if task["output"]:
                typer.echo("OUTPUT:")
                typer.echo(task["output"])
                typer.echo()
            if task["stderr"]:
                typer.echo("STDERR:")
                typer.echo(task["stderr"])
    except Exception as exc:
        if json_output:
            typer.echo(json.dumps({"status": "error", "message": str(exc)}))
        else:
            typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def wait(
    task_id: str = typer.Argument(..., help="Task UUID (full or 8-char suffix)"),
    timeout: int = typer.Option(300, "--timeout", help="Timeout in seconds"),
):
    """Poll until task completes."""
    import time

    deadline = time.time() + timeout
    poll_interval = 0.5

    while time.time() < deadline:
        task = spawn_db.get_task(task_id)
        if not task:
            tasks = spawn_db.list_tasks()
            task = next((t for t in tasks if t["task_id"].endswith(task_id)), None)

        if not task:
            typer.echo(f"❌ Task not found: {task_id}", err=True)
            raise typer.Exit(code=1)

        if task["status"] in ("completed", "failed", "timeout"):
            typer.echo(f"✓ Task {task_id[:8]} {task['status']}")
            raise typer.Exit(code=0 if task["status"] == "completed" else 1)

        time.sleep(poll_interval)

    typer.echo(f"❌ Task {task_id[:8]} timeout (exceeded {timeout}s)", err=True)
    raise typer.Exit(code=1)


@app.command()
def kill(
    task_id: str = typer.Argument(..., help="Task UUID (full or 8-char suffix)"),
):
    """Terminate a runaway task (future)."""
    typer.echo("❌ Task termination not yet implemented.")
    raise typer.Exit(code=1)
