from datetime import datetime

import typer

def display_context(timeline, current_state, lattice_docs):
    if timeline:
        typer.echo("## EVOLUTION (last 10)\n")
        for entry in timeline:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
            typ = entry["type"]
            identity_str = entry["identity"] or "system"
            data = entry["data"][:100] if entry["data"] else ""
            typer.echo(f"[{ts}] {typ} ({identity_str})")
            typer.echo(f"  {data}\n")

    if current_state["memory"] or current_state["knowledge"] or current_state["bridge"]:
        typer.echo("\n## CURRENT STATE\n")

        if current_state["memory"]:
            typer.echo(f"memory: {len(current_state['memory'])}")
            for r in current_state["memory"][:5]:
                typer.echo(f"  {r['topic']}: {r['message'][:80]}")
            typer.echo()

        if current_state["knowledge"]:
            typer.echo(f"knowledge: {len(current_state['knowledge'])}")
            for r in current_state["knowledge"][:5]:
                typer.echo(f"  {r['domain']}: {r['content'][:80]}")
            typer.echo()

        if current_state["bridge"]:
            typer.echo(f"bridge: {len(current_state['bridge'])}")
            for r in current_state["bridge"][:5]:
                typer.echo(f"  [{r['channel']}] {r['content'][:80]}")
            typer.echo()

    if lattice_docs:
        typer.echo("\n## LATTICE DOCS\n")
        for heading, content in lattice_docs.items():
            typer.echo(f"### {heading}\n")
            preview = "\n".join(content.split("\n")[:5])
            typer.echo(f"{preview}...\n")
