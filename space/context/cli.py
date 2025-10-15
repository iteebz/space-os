"Unified concept retrieval: evolution + current state + lattice."

import json

import typer

from space.lib import errors

from ..lib import readme
from ..lib.paths import canon_path
from . import (
    db,  # Add this import
    display,  # Add this import
)

errors.install_error_handler("context")

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main_command(
    ctx: typer.Context,
    topic: str | None = typer.Argument(None, help="Topic to retrieve context for"),
    identity: str | None = typer.Option(None, "--as", help="Scope to identity (default: all)"),
    all_agents: bool = typer.Option(False, "--all", help="Cross-agent perspective"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Unified context retrieval: trace evolution + current state + lattice docs."""
    if (ctx.resilient_parsing or ctx.invoked_subcommand is None) and not topic:
        try:
            protocol_content = readme.load("context")  # Use readme.load
            typer.echo(protocol_content)
        except (FileNotFoundError, ValueError) as e:
            typer.echo(f"❌ context README not found: {e}")
        return

    # Original logic for context retrieval
    timeline = db.collect_timeline(topic, identity, all_agents)  # Call from db module
    current_state = db.collect_current_state(topic, identity, all_agents)  # Call from db module
    lattice_docs = _search_lattice(topic)
    canon_docs = _search_canon(topic)  # New: Search canon documents

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "evolution": timeline,
                    "state": current_state,
                    "lattice": lattice_docs,
                    "canon": canon_docs,
                }
            )
        )
        return

    if quiet_output:
        return

    display.display_context(
        timeline, current_state, lattice_docs, canon_docs
    )  # Call display function with canon_docs

    if not timeline and not any(current_state.values()) and not lattice_docs and not canon_docs:
        typer.echo(f"No context found for '{topic}'")


def _search_lattice(topic: str):
    """Search README for relevant sections."""
    try:
        content = readme.README.read_text()
        lines = content.split("\n")
        matches = {}

        for line in lines:
            if line.startswith("#") and topic.lower() in line.lower():
                heading = line.strip()
                try:
                    section_content = readme.load_section(heading)
                    matches[heading] = section_content
                except ValueError:
                    pass

        return matches
    except Exception:
        return {}


def _search_canon(topic: str) -> dict:
    """Search canon documents for relevant sections."""
    matches = {}
    try:
        canon_root = canon_path()
        if not canon_root.exists():
            return {}

        for md_file in canon_root.rglob("*.md"):
            try:
                content = md_file.read_text()
                if topic.lower() in content.lower():
                    matches[str(md_file.relative_to(canon_root))] = content
            except Exception:
                pass
    except Exception:
        pass
    return matches


def main() -> None:
    """Entry point for poetry script."""
    app()
