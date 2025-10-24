import json

import typer

from space.os.core.spawn import db as spawn_db

app = typer.Typer()


def _resolve_agent_id(fuzzy_match: str, include_archived: bool = False) -> tuple[str, str] | None:
    """Resolve agent ID from partial UUID or identity name. Returns (agent_id, display_name)."""
    with spawn_db.connect() as conn:
        where_clause = "" if include_archived else "WHERE archived_at IS NULL"
        rows = conn.execute(f"SELECT agent_id, name FROM agents {where_clause}").fetchall()

    candidates = []
    for row in rows:
        agent_id = row["agent_id"]
        name = row["name"]

        if agent_id.startswith(fuzzy_match) or name and name.lower() == fuzzy_match.lower():
            candidates.append((agent_id, name))

    if len(candidates) == 1:
        agent_id, name = candidates[0]
        resolved = (
            spawn_db.get_identity(name)
            if (name and len(name) == 36 and name.count("-") == 4)
            else name
        )
        return (agent_id, resolved or name or agent_id[:8])

    return None


@app.command()
def describe(
    identity: str = typer.Option(..., "--as", help="Identity to describe"),
    description: str = typer.Argument(None, help="Description to set"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
):
    """Get or set self-description for an identity."""
    if description:
        updated = spawn_db.set_self_description(identity, description)
        if json_output:
            typer.echo(
                json.dumps({"identity": identity, "description": description, "updated": updated})
            )
        elif updated:
            typer.echo(f"{identity}: {description}")
        else:
            typer.echo(f"No agent: {identity}")
    else:
        desc = spawn_db.get_self_description(identity)
        if json_output:
            typer.echo(json.dumps({"identity": identity, "description": desc}))
        elif desc:
            typer.echo(desc)
        else:
            typer.echo(f"No self-description for {identity}")
