import typer

from ..spawn import canonical, registry

app = typer.Typer()


@app.command()
def link(
    orphan_id: str = typer.Argument(..., help="Orphan agent ID to link"),
    canonical_id: str = typer.Argument(..., help="Canonical agent ID to link to"),
):
    """Link orphan agent ID to canonical identity."""
    registry.init_db()
    
    with registry.get_db() as conn:
        orphan = conn.execute("SELECT id, name FROM agents WHERE id = ?", (orphan_id,)).fetchone()
        if not orphan:
            typer.echo(f"Orphan agent {orphan_id} not found")
            raise typer.Exit(1)
        
        canonical_agent = conn.execute("SELECT id, name FROM agents WHERE id = ?", (canonical_id,)).fetchone()
        if not canonical_agent:
            typer.echo(f"Canonical agent {canonical_id} not found")
            raise typer.Exit(1)
    
    canonical.set_canonical(orphan_id, canonical_id)
    typer.echo(f"Linked {orphan['name'] or orphan_id} → {canonical_agent['name'] or canonical_id}")


@app.command()
def rename(
    old_name: str = typer.Argument(..., help="Current agent name"),
    new_name: str = typer.Argument(..., help="New agent name"),
):
    """Rename an agent."""
    registry.init_db()
    
    success = registry.rename_agent(old_name, new_name)
    if success:
        typer.echo(f"Renamed {old_name} → {new_name}")
    else:
        typer.echo(f"Agent {old_name} not found")
        raise typer.Exit(1)


@app.command()
def alias(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    alias_name: str = typer.Argument(..., help="Alias to add"),
):
    """Add alias for agent."""
    registry.init_db()
    
    with registry.get_db() as conn:
        agent = conn.execute("SELECT id, name FROM agents WHERE id = ?", (agent_id,)).fetchone()
        if not agent:
            typer.echo(f"Agent {agent_id} not found")
            raise typer.Exit(1)
    
    canonical.add_alias(agent_id, alias_name)
    typer.echo(f"Added alias '{alias_name}' for {agent['name'] or agent_id}")


@app.command()
def show(
    name: str = typer.Argument(..., help="Agent name or alias"),
):
    """Show agent details."""
    registry.init_db()
    
    agent_id = registry.get_agent_id(name)
    if not agent_id:
        typer.echo(f"Agent {name} not found")
        raise typer.Exit(1)
    
    with registry.get_db() as conn:
        agent = conn.execute(
            "SELECT id, name, self_description, canonical_id FROM agents WHERE id = ?",
            (agent_id,)
        ).fetchone()
        
        typer.echo(f"ID: {agent['id']}")
        typer.echo(f"Name: {agent['name'] or '(unnamed)'}")
        if agent['self_description']:
            typer.echo(f"Self: {agent['self_description']}")
        if agent['canonical_id']:
            canonical_agent = conn.execute(
                "SELECT name FROM agents WHERE id = ?", (agent['canonical_id'],)
            ).fetchone()
            typer.echo(f"Canonical: {canonical_agent['name'] or agent['canonical_id']}")
        
        aliases = canonical.get_aliases(agent_id)
        if aliases:
            typer.echo(f"Aliases: {', '.join(aliases)}")
