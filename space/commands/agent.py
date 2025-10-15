import json

import typer

from space.spawn import registry

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main(
    ctx: typer.Context,
):
    pass


@app.command("list")
def list_agents(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output."),
):
    """List all registered agents."""

    agents = registry.list_all_agents()
    if json_output:
        typer.echo(json.dumps(agents, indent=2))
    elif not quiet_output:
        if agents:
            for agent_name in agents:
                typer.echo(agent_name)
        else:
            typer.echo("No agents registered.")
