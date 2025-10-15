import typer

from space.spawn import registry
from space.lib.cli_utils import common_cli_options

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main(
    ctx: typer.Context,
):
    pass


@app.command("list")
@common_cli_options
def list_agents(
    ctx: typer.Context,
):
    """List all registered agents."""
    json_output = ctx.obj.get("json_output")
    quiet_output = ctx.obj.get("quiet_output")

    agents = registry.list_all_agents()
    if json_output:
        typer.echo(json.dumps(agents, indent=2))
    elif not quiet_output:
        if agents:
            for agent_name in agents:
                typer.echo(agent_name)
        else:
            typer.echo("No agents registered.")
