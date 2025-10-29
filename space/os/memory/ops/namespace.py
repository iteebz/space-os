import typer

from space.os.memory import api  # Import the api module directly


def resolve_agent_id(ctx: typer.Context) -> str:
    identity = ctx.obj.get("identity")
    if not identity:
        raise typer.BadParameter("Agent identity must be provided via --as option.")
    return identity


def add_entry(ctx: typer.Context, topic: str, message: str):
    agent_id = resolve_agent_id(ctx)
    return api.add_entry(agent_id=agent_id, topic=topic, message=message, source="manual")


def list_entries(ctx: typer.Context, topic: str, show_all: bool):
    agent_id = resolve_agent_id(ctx)
    return api.list_entries(agent_id=agent_id, topic=topic, show_all=show_all)


def archive_entry(ctx: typer.Context, uuid: str, restore: bool):
    resolve_agent_id(ctx)
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        if restore:
            api.restore_entry(uuid)
            return "restored"
        api.archive_entry(uuid)
        return "archived"
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def core_entry(ctx: typer.Context, uuid: str, unmark: bool):
    resolve_agent_id(ctx)
    entry = api.get_by_id(uuid)
    if not entry:
        raise typer.BadParameter(f"Entry not found: {uuid}")
    try:
        is_core = not unmark
        api.mark_core(uuid, core=is_core)
        return is_core
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def replace_entry(ctx: typer.Context, old_id: str, message: str, note: str):
    agent_id = resolve_agent_id(ctx)

    old_entry = api.get_by_id(old_id)
    if not old_entry:
        raise typer.BadParameter(f"Not found: {old_id}")

    try:
        return api.replace_entry([old_id], agent_id, old_entry.topic, message, note)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
