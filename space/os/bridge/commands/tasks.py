import json
from datetime import datetime

import typer

from .. import db as bridge_db

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
        conn = bridge_db.get_db()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if identity:
            query += " AND identity = ?"
            params.append(identity)
        if channel:
            channel_id = api.resolve_channel_id(channel)
            query += " AND channel_id = ?"
            params.append(channel_id)

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()
        conn.close()

        if not rows:
            if not quiet_output:
                typer.echo("No tasks found.")
            return

        if json_output:
            tasks = [dict(row) for row in rows]
            typer.echo(json.dumps(tasks, indent=2))
        elif not quiet_output:
            typer.echo("TASKS:")
            for row in rows:
                task_id = row["uuid7"][-8:]
                task_status = row["status"]
                task_identity = row["identity"]
                created = row["created_at"]
                duration = ""
                if row["started_at"] and row["completed_at"]:
                    dt = datetime.fromisoformat(row["completed_at"]) - datetime.fromisoformat(
                        row["started_at"]
                    )
                    duration = f" ({int(dt.total_seconds())}s)"
                typer.echo(f"  [{task_id}] {task_status:10} {task_identity:15} {created}{duration}")
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
        conn = bridge_db.get_db()

        query = "SELECT * FROM tasks WHERE uuid7 LIKE ? OR uuid7 = ?"
        row = conn.execute(query, (f"%{task_id}", task_id)).fetchone()
        conn.close()

        if not row:
            typer.echo(f"❌ Task not found: {task_id}", err=True)
            raise typer.Exit(code=1)

        if json_output:
            task = dict(row)
            typer.echo(json.dumps(task, indent=2))
        else:
            typer.echo(f"Task: {row['uuid7'][-8:]}")
            typer.echo(f"Status: {row['status']}")
            typer.echo(f"Identity: {row['identity']}")
            typer.echo()
            if row["input"]:
                typer.echo("INPUT:")
                typer.echo(row["input"])
                typer.echo()
            if row["output"]:
                typer.echo("OUTPUT:")
                typer.echo(row["output"])
                typer.echo()
            if row["stderr"]:
                typer.echo("STDERR:")
                typer.echo(row["stderr"])
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
        conn = bridge_db.get_db()
        query = "SELECT status FROM tasks WHERE uuid7 LIKE ? OR uuid7 = ?"
        row = conn.execute(query, (f"%{task_id}", task_id)).fetchone()
        conn.close()

        if not row:
            typer.echo(f"❌ Task not found: {task_id}", err=True)
            raise typer.Exit(code=1)

        if row["status"] in ("completed", "failed", "timeout"):
            typer.echo(f"✓ Task {task_id[:8]} {row['status']}")
            raise typer.Exit(code=0 if row["status"] == "completed" else 1)

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
