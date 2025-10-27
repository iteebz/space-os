"""Spawn CLI commands: typer entry point."""

import click
import typer
from typer.core import TyperGroup

from space.lib import errors, output, readme
from space.os.spawn import api, models

errors.install_error_handler("spawn")


class AgentSpawnGroup(TyperGroup):
    """Typer group that dynamically spawns tasks for agent names."""

    def get_command(self, ctx, cmd_name):
        """Get command by name, or spawn agent if not found."""
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        agent = api.get_agent(cmd_name)
        if agent is None:
            return None

        @click.command(name=cmd_name)
        @click.argument("task_input", required=False, nargs=-1)
        def spawn_agent(task_input):
            input_list = list(task_input) if task_input else []
            api.launch_agent(agent.identity, extra_args=input_list)

        return spawn_agent


app = typer.Typer(invoke_without_command=True, cls=AgentSpawnGroup)

from . import agents, launch, sleep, tasks, wake  # noqa: E402

app.command("agents")(agents.list_agents)
app.add_typer(tasks.app, name="tasks")
app.command()(wake.wake)
app.add_typer(sleep.sleep, name="sleep")
app.command()(launch.launch)


@app.callback()
def main_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Spawn: Agent Management & Task Orchestration"""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(readme.load("spawn"))


@app.command("merge")
def merge(id_from: str, id_to: str):
    """Merge all data from one agent ID to another."""
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


@app.command("register")
def register(
    identity: str,
    provider: str = typer.Option(
        ...,
        "--provider",
        "-p",
        help="Provider: claude, codex, or gemini. Run 'spawn models' to list available options",
    ),
    model: str = typer.Option(
        ..., "--model", "-m", help="Model ID. Run 'spawn models' to list available models"
    ),
    constitution: str | None = typer.Option(
        None, "--constitution", "-c", help="Constitution filename (e.g., zealot.md) - optional"
    ),
):
    """Register a new agent."""
    try:
        agent_id = api.register_agent(identity, provider, model, constitution)
        typer.echo(f"✓ Registered {identity} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command("update")
def update(
    identity: str,
    constitution: str = typer.Option(None, "--constitution", "-c", help="Constitution filename"),
    provider: str = typer.Option(
        None, "--provider", "-p", help="Provider: claude, gemini, or codex"
    ),
    model: str = typer.Option(None, "--model", "-m", help="Full model name"),
):
    """Update agent fields."""
    try:
        api.update_agent(identity, constitution, provider, model)
        typer.echo(f"✓ Updated {identity}")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command("clone")
def clone(src: str, dst: str):
    """Clone an agent with new identity."""
    try:
        agent_id = api.clone_agent(src, dst)
        typer.echo(f"✓ Cloned {src} → {dst} ({agent_id[:8]})")
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command("rename")
def rename(old_name: str, new_name: str):
    """Rename an agent."""
    try:
        if api.rename_agent(old_name, new_name):
            typer.echo(f"✓ Renamed {old_name} → {new_name}")
        else:
            typer.echo(f"❌ Agent not found: {old_name}. Run `spawn` to list agents.", err=True)
            raise typer.Exit(1)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1) from e


@app.command("models")
def list_models():
    """List available models for all providers."""
    for prov in ["claude", "codex", "gemini"]:
        provider_models = models.get_models_for_provider(prov)
        typer.echo(f"\n📦 {prov.capitalize()} Models:\n")
        for model in provider_models:
            typer.echo(f"  • {model.name} ({model.id})")
            if model.description:
                typer.echo(f"    {model.description}")
            if model.reasoning_levels:
                typer.echo(f"    Reasoning levels: {', '.join(model.reasoning_levels)}")
            typer.echo()
