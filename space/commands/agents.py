import json
from pathlib import Path

import typer

from ..spawn import registry

app = typer.Typer(invoke_without_command=True)


def _extract_flags(ctx: typer.Context) -> tuple[bool, bool]:
    """Extract json/quiet flags from parent callback context."""
    parent = ctx.parent
    if parent and isinstance(parent.obj, dict):
        return parent.obj.get("json_output", False), parent.obj.get("quiet_output", False)
    return False, False


def _list_agents(json_output: bool, quiet_output: bool):
    """Render registered agents honoring output flags."""
    registry.init_db()
    regs = registry.list_registrations()
    if not regs:
        if json_output:
            typer.echo(json.dumps([]))
        elif not quiet_output:
            typer.echo("No agents registered")
        return

    seen = set()
    unique_agents = []
    for reg in regs:
        if reg.agent_name not in seen:
            seen.add(reg.agent_name)
            self_desc = registry.get_self_description(reg.agent_name)
            unique_agents.append({"agent_name": reg.agent_name, "description": self_desc})

    if json_output:
        typer.echo(json.dumps(unique_agents))
    elif not quiet_output:
        for agent in unique_agents:
            if agent["description"]:
                typer.echo(f"{agent['agent_name']}: {agent['description']}")
            else:
                typer.echo(agent["agent_name"])


@app.callback()
def agents_root(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Agent registry tooling (defaults to listing)."""
    ctx.obj = {"json_output": json_output, "quiet_output": quiet_output}
    if ctx.invoked_subcommand is None:
        _list_agents(json_output, quiet_output)
        raise typer.Exit()


@app.command("list")
def list_agents(
    ctx: typer.Context,
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """List registered agents."""
    parent_json, parent_quiet = _extract_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    _list_agents(json_output, quiet_output)


@app.command("describe")
def describe_agent(
    ctx: typer.Context,
    identity: str = typer.Argument(..., help="Identity to describe"),
    description: str = typer.Argument(..., help="Description of the identity"),
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Set self-description for an identity."""
    parent_json, parent_quiet = _extract_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    registry.init_db()
    updated = registry.set_self_description(identity, description)
    payload = {"identity": identity, "description": description, "updated": updated}

    if json_output:
        typer.echo(json.dumps(payload))
        return

    if quiet_output:
        return

    if updated:
        typer.echo(f"{identity}: {description}")
    else:
        typer.echo(f"No agent: {identity}")


@app.command("show")
def show_agent(
    ctx: typer.Context,
    identity: str = typer.Argument(..., help="Identity to inspect"),
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Display self-description for an identity."""
    parent_json, parent_quiet = _extract_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    registry.init_db()
    desc = registry.get_self_description(identity)
    payload = {"identity": identity, "description": desc}

    if json_output:
        typer.echo(json.dumps(payload))
        return

    if quiet_output:
        return

    if desc:
        typer.echo(desc)
    else:
        typer.echo(f"No self-description for {identity}")


@app.command("delete")
def delete_agent(
    ctx: typer.Context,
    identity: str = typer.Argument(..., help="Identity to delete"),
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Delete an agent from the registry."""
    parent_json, parent_quiet = _extract_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag
    registry.init_db()
    registry.delete_agent(identity)

    if json_output:
        typer.echo(json.dumps({"identity": identity, "deleted": True}))
    elif not quiet_output:
        typer.echo(f"Deleted {identity}")


@app.command("config")
def show_agent_config(
    ctx: typer.Context,
    json_flag: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_flag: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """Show configured agent binaries (claude, gemini, codex)."""
    from ..spawn import spawn

    parent_json, parent_quiet = _extract_flags(ctx)
    json_output = parent_json or json_flag
    quiet_output = parent_quiet or quiet_flag

    cfg = spawn.load_config()
    agents = cfg.get("agents", {})

    if json_output:
        typer.echo(json.dumps(agents))
        return

    if quiet_output:
        return

    if not agents:
        typer.echo("No agents configured")
        return

    typer.echo(f"{'AGENT':<10} {'COMMAND':<15} {'TARGETS'}")
    typer.echo("-" * 60)
    for name, agent_cfg in agents.items():
        cmd = agent_cfg.get("command", "")
        targets = agent_cfg.get("identity_targets", [])
        if isinstance(targets, list):
            targets_str = ", ".join([Path(t).name for t in targets])
        else:
            targets_str = Path(targets).name if targets else ""
        typer.echo(f"{name:<10} {cmd:<15} {targets_str}")
