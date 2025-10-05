import sys

import click

from . import registry, spawner

CONTEXT_SETTINGS = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}


class SpawnGroup(click.Group):
    """Custom group that falls back to inline launch syntax."""

    def resolve_command(self, ctx: click.Context, args):  # type: ignore[override]
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError:
            if not args:
                raise

        if args:
            inline = self.commands.get("_inline_launch")
            if inline is not None:
                return "_inline_launch", inline, args

        # If no inline handler, re-raise original resolution error.
        return super().resolve_command(ctx, args)


@click.group(
    cls=SpawnGroup,
    invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
)
@click.pass_context
def main(ctx: click.Context):
    """Constitutional agent registry"""
    registry.init_db()

    if ctx.invoked_subcommand is not None:
        return

    if not ctx.args:
        click.echo(ctx.get_help())
        ctx.exit()


@main.command()
@click.argument("role")
@click.argument("sender_id")
@click.argument("topic")
def register(role: str, sender_id: str, topic: str):
    """Register constitutional agent"""
    try:
        result = spawner.register_agent(role, sender_id, topic)
        click.echo(
            f"Registered: {result['role']} → {result['sender_id']} on {result['topic']} "
            f"(constitution: {result['constitution_hash']})"
        )
    except Exception as e:
        click.echo(f"Registration failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("role")
@click.argument("sender_id")
@click.argument("topic")
def unregister(role: str, sender_id: str, topic: str):
    """Unregister agent"""
    try:
        reg = registry.get_registration(role, sender_id, topic)
        if not reg:
            click.echo(f"Registration not found: {role} {sender_id} {topic}", err=True)
            sys.exit(1)

        registry.unregister(role, sender_id, topic)
        click.echo(f"Unregistered: {role} ({sender_id})")
    except Exception as e:
        click.echo(f"Unregister failed: {e}", err=True)
        sys.exit(1)


@main.command(name="list")
def list_registrations():
    """List registered agents"""
    regs = registry.list_registrations()
    if not regs:
        click.echo("No registrations found")
        return

    click.echo(f"{'ROLE':<15} {'SENDER':<15} {'TOPIC':<20} {'HASH':<10} {'REGISTERED':<20}")
    click.echo("-" * 90)
    for r in regs:
        click.echo(
            f"{r.role:<15} {r.sender_id:<15} {r.topic:<20} "
            f"{r.constitution_hash[:8]:<10} {r.registered_at:<20}"
        )


@main.command()
@click.argument("role")
def constitution(role: str):
    """Get constitution path for role"""
    try:
        path = spawner.get_constitution_path(role)
        click.echo(str(path))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command(context_settings=CONTEXT_SETTINGS)
@click.argument("role")
@click.option(
    "--agent",
    help="The agent to spawn (e.g., gemini, claude). Uses role default if not specified.",
)
@click.pass_context
def launch(ctx: click.Context, role: str, agent: str | None):
    """Launches an agent with a specific constitutional role."""
    try:
        spawner.launch_agent(role, agent, extra_args=list(ctx.args))
    except Exception as e:
        click.echo(f"Launch failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("base_identity")
def identity(base_identity: str):
    """Get bridge identity file path"""
    from . import config

    identity_file = config.bridge_identities_dir() / f"{base_identity}.md"
    click.echo(str(identity_file))


@main.command(name="_inline_launch", hidden=True, context_settings=CONTEXT_SETTINGS)
@click.pass_context
def _inline_launch(ctx: click.Context):
    """Handle implicit launch invocation (`spawn <role> ...`)."""

    role, agent, extra_args = _parse_inline_launch_args(ctx.args)
    try:
        spawner.launch_agent(role, agent, extra_args=extra_args)
    except Exception as e:
        click.echo(f"Launch failed: {e}", err=True)
        ctx.exit(1)


def _parse_inline_launch_args(args: list[str]) -> tuple[str, str | None, list[str]]:
    """Parse inline spawn launch invocation.

    Supports:
    - spawn <role>
    - spawn <role> --agent <agent>
    - spawn <role> --<agent>
    """

    role = args[0]
    agent: str | None = None
    passthrough: list[str] = []

    configured_agents = set(spawner.load_config().get("agents", {}).keys())

    idx = 1
    while idx < len(args):
        token = args[idx]
        if token == "--":
            passthrough.extend(args[idx + 1 :])
            break

        if not token.startswith("--"):
            if token in configured_agents:
                agent = token
            else:
                passthrough.append(token)
            idx += 1
            continue

        option = token[2:]
        if not option:
            raise click.UsageError("Invalid agent flag")

        if option in {"agent", "as"}:
            idx += 1
            if idx >= len(args):
                raise click.UsageError(f"--{option} requires a value")
            agent = args[idx]
        elif option in configured_agents:
            agent = option
        else:
            passthrough.append(token)
            if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                passthrough.append(args[idx + 1])
                idx += 1
        idx += 1

    return role, agent, passthrough


if __name__ == "__main__":
    main()
