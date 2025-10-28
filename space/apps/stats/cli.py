import typer

from space.apps import stats as stats_app

app = typer.Typer(invoke_without_command=True)


def overview():
    """Show space overview."""
    s = stats_app.collect(agent_limit=10)

    lines = [
        """
   ___ _ __   __ _  ___ ___
  / __| '_ \\ / _` |/ __/ _ \\
 _\\__ \\ |_) | (_| | (_|  __/
(_)___/ .__/ \\__,_|\\___\\___|
      | |
      |_|

overview"""
    ]

    if s.spawn.available and s.spawn.total > 0:
        lines.append(
            f"  spawn · {s.spawn.total} spawns · {s.spawn.agents} agents · {s.spawn.hashes} hashes"
        )

    if s.bridge.available:
        lines.append(
            f"  bridge · {s.bridge.active_channels} active · {s.bridge.archived_channels} archived · {s.bridge.active} msgs ({s.bridge.archived} archived)"
        )

    if s.memory.available and s.memory.total > 0:
        archived = s.memory.total - s.memory.active
        lines.append(
            f"  memory · {s.memory.active} active · {archived} archived · {s.memory.topics} topics"
        )

    if s.knowledge.available and s.knowledge.total > 0:
        archived_k = s.knowledge.total - s.knowledge.active
        lines.append(
            f"  knowledge · {s.knowledge.active} active · {archived_k} archived · {s.knowledge.topics} domains"
        )

    if s.agents:
        lines.append("\nagents")
        lines.append("  name · id · e-s-b-m-k")

        sorted_agents = sorted(
            s.agents, key=lambda a: int(a.last_active) if a.last_active else 0, reverse=True
        )

        for a in sorted_agents:
            parts = [a.identity]
            parts.append(f"{a.events}-{a.spawns}-{a.msgs}-{a.mems}-{a.knowledge}")
            lines.append("  " + " · ".join(parts))

    typer.echo("\n".join(lines) + "\n")


@app.callback(invoke_without_command=True)
def main_command(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        overview()


@app.command()
def memory():
    """Memory lattice health analytics."""
    s = stats_app.collect()

    if not s.memory.available:
        typer.echo("memory not initialized")
        return

    lines = ["memory lattice health\n"]

    total = s.memory.total
    active = s.memory.active
    archived = total - active
    topics = s.memory.topics

    if total == 0:
        lines.append("  no entries yet")
    else:
        retention_rate = (active / total * 100) if total > 0 else 0
        avg_per_topic = active / topics if topics > 0 else 0

        lines.append(f"  nodes · {active} active · {archived} archived")
        lines.append(f"  topics · {topics} domains")
        lines.append(f"  retention · {retention_rate:.1f}%")
        lines.append(f"  density · {avg_per_topic:.1f} nodes/topic")

        if s.memory.leaderboard:
            lines.append("\n  contributors")
            for entry in s.memory.leaderboard[:10]:
                lines.append(f"    {entry.identity} · {entry.count}")

    typer.echo("\n".join(lines) + "\n")


@app.command()
def knowledge():
    """Knowledge graph health analytics."""
    s = stats_app.collect()

    if not s.knowledge.available:
        typer.echo("knowledge not initialized")
        return

    lines = ["knowledge graph health\n"]

    total = s.knowledge.total
    active = s.knowledge.active
    archived = total - active
    domains = s.knowledge.topics

    if total == 0:
        lines.append("  no entries yet")
    else:
        retention_rate = (active / total * 100) if total > 0 else 0
        avg_per_domain = active / domains if domains > 0 else 0

        lines.append(f"  nodes · {active} active · {archived} archived")
        lines.append(f"  domains · {domains}")
        lines.append(f"  retention · {retention_rate:.1f}%")
        lines.append(f"  density · {avg_per_domain:.1f} nodes/domain")

        if s.knowledge.leaderboard:
            lines.append("\n  contributors")
            for entry in s.knowledge.leaderboard[:10]:
                lines.append(f"    {entry.identity} · {entry.count}")

    typer.echo("\n".join(lines) + "\n")


@app.command()
def bridge():
    """Bridge channel health analytics."""
    s = stats_app.collect()

    if not s.bridge.available:
        typer.echo("bridge not initialized")
        return

    lines = ["bridge channel health\n"]

    total = s.bridge.total
    active = s.bridge.active
    archived = s.bridge.archived
    channels = s.bridge.active_channels
    archived_channels = s.bridge.archived_channels

    if total == 0:
        lines.append("  no messages yet")
    else:
        retention_rate = (active / total * 100) if total > 0 else 0
        avg_per_channel = active / channels if channels > 0 else 0

        lines.append(f"  messages · {active} active · {archived} archived")
        lines.append(f"  channels · {channels} active · {archived_channels} archived")
        lines.append(f"  retention · {retention_rate:.1f}%")
        lines.append(f"  density · {avg_per_channel:.1f} msgs/channel")

        if s.bridge.message_leaderboard:
            lines.append("\n  contributors")
            for entry in s.bridge.message_leaderboard[:10]:
                lines.append(f"    {entry.identity} · {entry.count}")

    typer.echo("\n".join(lines) + "\n")
