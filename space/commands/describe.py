import json

import typer

from ..spawn import registry


def describe(
    identity: str = typer.Option(..., "--as", help="Identity to describe"),
    description: str = typer.Argument(None, help="Description to set"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """Get or set self-description for an identity."""
    registry.init_db()

    if description:
        updated = registry.set_self_description(identity, description)
        if json_output:
            typer.echo(
                json.dumps({"identity": identity, "description": description, "updated": updated})
            )
        elif updated:
            typer.echo(f"{identity}: {description}")
        else:
            typer.echo(f"No agent: {identity}")
    else:
        desc = registry.get_self_description(identity)
        if json_output:
            typer.echo(json.dumps({"identity": identity, "description": desc}))
        elif desc:
            typer.echo(desc)
        else:
            typer.echo(f"No self-description for {identity}")
