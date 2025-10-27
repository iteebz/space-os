"""Spawn CLI commands: typer entry point."""

import click
import typer
from typer.core import TyperGroup

from space.lib import errors, output
from space.os.spawn import api

errors.install_error_handler("spawn")


class SpawnGroup(TyperGroup):
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
            api.spawn_agent(agent.identity, extra_args=input_list)

        return spawn_agent


app = typer.Typer(invoke_without_command=True, cls=SpawnGroup)

from . import (  # noqa: E402
    agents,
    clone,
    merge,
    models,
    register,
    rename,
    sleep,
    tasks,
    update,
)

app.command("agents")(agents.list_agents)
app.add_typer(tasks.app, name="tasks")
app.add_typer(sleep.sleep, name="sleep")
app.command()(merge.merge)
app.command()(register.register)
app.command()(update.update)
app.command()(clone.clone)
app.command()(rename.rename)
app.command("models")(models.list_models)


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
        typer.echo("spawn <agent>: Launch agent. Run 'spawn agents' to list registered agents.")
