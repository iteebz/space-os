"""Identity resolution for CLI commands."""

import os
from collections.abc import Callable

import typer

from space.core.models import Agent


def resolve_identity(explicit: str | None) -> str | None:
    """Resolve identity from explicit arg or SPACE_IDENTITY env var."""
    return explicit or os.environ.get("SPACE_IDENTITY")


def require_identity(explicit: str | None) -> str:
    """Resolve identity, raising if not found."""
    identity = resolve_identity(explicit)
    if not identity:
        raise ValueError("Identity required: use --as or set SPACE_IDENTITY")
    return identity


def require_agent(func: Callable) -> Callable:
    """Decorator: resolve identity and fetch agent, or raise error.

    Injects Agent object as 'agent' keyword argument.

    Usage:
        @require_agent
        def add(ctx, agent: Agent, message: str):
            api.add_memory(agent.agent_id, message)
    """

    def wrapper(ctx: typer.Context, *args, **kwargs):
        from space.os import spawn

        identity = resolve_identity(ctx.obj.get("identity") if ctx.obj else None)
        if not identity:
            raise typer.BadParameter("--as required or set SPACE_IDENTITY")

        agent = spawn.get_agent(identity)
        if not agent:
            raise typer.BadParameter(f"Identity '{identity}' not registered.")

        kwargs["agent"] = agent
        return func(ctx, *args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def resolve_agent(ctx: typer.Context) -> Agent:
    """Resolve agent from context or raise error."""
    from space.os import spawn

    identity = resolve_identity(ctx.obj.get("identity") if ctx.obj else None)
    if not identity:
        raise typer.BadParameter("--as required or set SPACE_IDENTITY")

    agent = spawn.get_agent(identity)
    if not agent:
        raise typer.BadParameter(f"Identity '{identity}' not registered.")

    return agent
