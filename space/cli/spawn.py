import sys

import click

from space.spawn import config, registry, spawner

CONTEXT_SETTINGS = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}


@click.group(
    invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def spawn_group(ctx: click.Context):
    """Constitutional agent registry"""
    registry.init_db()

    if ctx.invoked_subcommand is not None:
        return

    # Removed inline launch logic, now requires explicit subcommand
    if not ctx.args:
        click.echo(ctx.get_help())
        ctx.exit()


@spawn_group.command()
@click.argument("role")
@click.argument("sender_id")
@click.argument("topic")
@click.option("--model", help="Model to use (e.g., claude-4.5-sonnet, gpt-5-codex)")
@click.option("--provider", help="Provider of the model (e.g., openai, anthropic)")
@click.option("--self-description", help="Self-description of the agent")
def register(role: str, sender_id: str, topic: str, model: str | None, provider: str | None, self_description: str | None):
    """Register constitutional agent"""
    try:
        result = spawner.register_agent(role, sender_id, topic, model, provider)
        if self_description:
            registry.set_self_description(sender_id, self_description)
        provider_suffix = f" (provider: {result['provider']})" if result.get("provider") else ""
        self_description_suffix = f" (self_description: {self_description})" if self_description else ""
        click.echo(
            f"Registered: {result['role']} → {result['sender_id']} on {result['topic']} "
            f"(constitution: {result['constitution_hash']}){model_suffix}{provider_suffix}{self_description_suffix}"
        )
    except Exception as e:
        click.echo(f"Entry registration failed: {e}", err=True)
        sys.exit(1)


@spawn_group.command()
@click.argument("role")
@click.argument("sender_id")
@click.argument("topic")
def unregister(role: str, sender_id: str, topic: str):
    """Unregister agent"""
    try:
        reg = registry.fetch(sender_id, topic)
        if not reg:
            click.echo(f"Entry not found: {role} {sender_id} {topic}", err=True)
            sys.exit(1)

        registry.unregister(sender_id, topic)
        click.echo(f"Unregistered: {role} ({sender_id})")
    except Exception as e:
        click.echo(f"Unregister failed: {e}", err=True)
        sys.exit(1)


@spawn_group.command(name="list")
def spawn_list_entries():
    """List registered entries"""
    regs = registry.list()
    if not regs:
        click.echo("No entries found")
        return

    click.echo(f"{'AGENT ID':<20} {'ROLE':<20} {'CHANNELS':<30} {'PROVIDER':<15} {'MODEL':<20} {'SELF DESCRIPTION':<30}")
    click.echo("-" * 135)
    for r in regs:
        click.echo(f"{r.agent_id:<20} {r.role:<20} {r.channels:<30} {r.provider if r.provider else 'N/A':<15} {r.model if r.model else 'N/A':<20} {r.self if r.self else 'N/A':<30}")


@spawn_group.command()
@click.argument("role")
def constitution(role: str):
    """Get constitution path for role"""
    try:
        path = spawner.get_constitution_path(role)
        click.echo(str(path))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@spawn_group.command(context_settings=CONTEXT_SETTINGS)
@click.argument("role")
@click.option(
    "--agent",
    help="The agent to spawn (e.g., gemini, claude). Uses role default if not specified.",
)
@click.option("--model", help="Model override (e.g., claude-4.5-sonnet, gpt-5-codex)")
@click.option("--provider", help="Provider override (e.g., openai, anthropic)")
@click.option("--self-description", help="Self-description override")
@click.pass_context
def launch(ctx: click.Context, role: str, agent: str | None, model: str | None, provider: str | None, self_description: str | None):
    """Launches an agent with a specific constitutional role."""
    try:
        # extra_args are now passed directly from the main space command if any
        spawner.launch_agent(role, agent, extra_args=list(ctx.args), model=model, provider=provider, self_description=self_description)
    except Exception as e:
        click.echo(f"Launch failed: {e}", err=True)
        sys.exit(1)


@spawn_group.group()
def identity():
    """Manage identities."""
    pass


@identity.command(name="get")
@click.argument("base_identity")
def identity_get_command(base_identity: str):
    """Get identity constitution content."""
    try:
        entry = registry.fetch_by_sender(base_identity)
        if entry and entry.identity:
            click.echo(entry.identity)
        else:
            click.echo(f"Error: Identity '{base_identity}' not found in registry.", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@identity.command()
@click.option(
    "--as",
    "identity_name",
    required=True,
    help="The identity to show evolution for (e.g., zealot-1)",
)
def identity_evo_command(identity_name: str):
    """Show the chronological evolution of an identity's constitution."""
    try:
        entries = [e for e in registry.list() if e.agent_id == identity_name]

        if not entries:
            click.echo(f"No constitution history found for identity '{identity_name}'.", err=True)
            sys.exit(1)

        # Sort by registered_at to ensure chronological order
        entries.sort(key=lambda x: x.registered_at)

        for entry in entries:
            click.echo(f"\n--- Registered At: {entry.registered_at} ---")
            click.echo(f"--- Constitution Hash: {entry.constitution_hash} ---")
            click.echo(entry.identity)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@spawn_group.command()
@click.argument("old_sender_id")
@click.argument("new_sender_id")
@click.option("--self-description", help="New self-description (optional, keeps existing if not specified)")
@click.option("--provider", help="New provider (optional, keeps existing if not specified)")
@click.option("--model", help="New model (optional, keeps existing if not specified)")
def spawn_rename(old_sender_id: str, new_sender_id: str, self_description: str | None, provider: str | None, model: str | None):
    """Rename agent across all provenance systems"""

    try:
        regs = [r for r in registry.list() if r.agent_id == old_sender_id]
        if not regs:
            click.echo(f"No entries found for {old_sender_id}", err=True)
            sys.exit(1)

        if self_description:
            registry.set_self_description(new_sender_id, self_description)

        registry.rename_sender(old_sender_id, new_sender_id, new_self_description=self_description, new_provider=provider, new_model=model)

        bridge_db = config.workspace_root() / ".space" / "bridge.db"
        import sqlite3

        conn = sqlite3.connect(bridge_db)
        conn.execute(
            "UPDATE messages SET sender = ? WHERE sender = ?", (new_sender_id, old_sender_id)
        )
        conn.execute(
            "UPDATE bookmarks SET agent_id = ? WHERE agent_id = ?", (new_sender_id, old_sender_id)
        )
        conn.commit()
        conn.close()

        click.echo(
            f"Renamed {old_sender_id} → {new_sender_id}"
            + (f" (self_description: {self_description})" if self_description else "")
            + (f" (provider: {provider})" if provider else "")
            + (f" (model: {model})" if model else "")
        )
    except Exception as e:
        click.echo(f"Rename failed: {e}", err=True)
        sys.exit(1)
