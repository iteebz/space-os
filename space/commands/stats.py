import json
from dataclasses import asdict

import typer

from ..lib import stats as space_stats


def stats(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Show space statistics."""
    s = space_stats.collect()

    if json_output:
        typer.echo(json.dumps(asdict(s)))
        return

    if quiet_output:
        return

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
        inactive = s.bridge.channels - s.bridge.active_channels
        lines.append(
            f"  bridge · {s.bridge.active_channels} active · {inactive} idle · {s.bridge.total} msgs · {s.bridge.notes} notes"
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
        lines.append("  name · s-b-m-k · active")

        sorted_agents = sorted(
            [a for a in s.agents if a.last_active], key=lambda a: a.last_active, reverse=True
        )

        for a in sorted_agents[:15]:
            parts = [a.identity]
            parts.append(f"{a.spawns}-{a.msgs}-{a.mems}-{a.knowledge}")
            if a.last_active_human:
                parts.append(a.last_active_human)
            lines.append("  " + " · ".join(parts))

    typer.echo("\n".join(lines) + "\n")
