"Unified concept retrieval: evolution + current state + lattice."

import json

import typer

from space import readme
from space.lib import errors

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
    help_flag: bool = typer.Option(
        False,
        "--help",
        "-h",
        help="Show protocol instructions and command overview.",
        is_eager=True,
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
    quiet_output: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
):
    """Unified context retrieval: trace evolution + current state + lattice docs."""
    if help_flag:
        typer.echo(readme.load("context"))
        raise typer.Exit()
    if (ctx.resilient_parsing or ctx.invoked_subcommand is None) and not topic:
        typer.echo(readme.load("context"))
        return

    # Original logic for context retrieval
    timeline = db.collect_timeline(topic, identity, all_agents)  # Call from db module
    current_state = db.collect_current_state(topic, identity, all_agents)  # Call from db module
    lattice_docs = {}
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
            except Exception as e:
                errors.log_error("context", None, e, "_search_canon file processing")
    except Exception as e:
        errors.log_error("context", None, e, "_search_canon directory traversal")
    return matches


def main() -> None:
    """Entry point for poetry script."""
    app()
