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
