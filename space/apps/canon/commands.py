"""Space canon lookup - navigate and read documents from ~/space/canon."""

from pathlib import Path

import typer

from space.lib.paths import canon_path

app = typer.Typer(invoke_without_command=True, no_args_is_help=False)


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    doc_path: str | None = typer.Argument(None, help="Document path (e.g., INDEX.md or constitutions/zealot.md)"),
):
    """Navigate and read canon documents from ~/space/canon."""
    if ctx.invoked_subcommand is not None:
        return

    canon_root = canon_path()
    if not canon_root.exists():
        typer.echo(f"Error: Canon directory not found at {canon_root}", err=True)
        raise typer.Exit(1)

    if not doc_path:
        _show_tree(canon_root)
        return

    _read_document(canon_root, doc_path)


def _show_tree(canon_root: Path) -> None:
    """Display tree of canon documents."""
    typer.echo("\nCanon structure. Navigate with: space canon <path>")
    typer.echo("Examples: space canon INDEX.md  |  space canon constitutions/zealot.md\n")
    _print_tree(canon_root, canon_root, prefix="")


def _print_tree(path: Path, root: Path, prefix: str, max_depth: int = 3, depth: int = 0) -> None:
    """Recursively print directory tree."""
    if depth >= max_depth:
        return

    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

    for i, item in enumerate(items):
        if item.name.startswith("."):
            continue

        is_last = i == len(items) - 1
        current_prefix = "└── " if is_last else "├── "
        typer.echo(f"{prefix}{current_prefix}{item.name}")

        if item.is_dir():
            next_prefix = prefix + ("    " if is_last else "│   ")
            _print_tree(item, root, next_prefix, max_depth, depth + 1)


def _read_document(canon_root: Path, doc_path: str) -> None:
    """Read full document from canon."""
    target = canon_root / doc_path
    if not target.exists():
        target = canon_root / f"{doc_path}.md"

    if not target.exists():
        typer.echo(f"Document not found: {doc_path}")
        available = list(canon_root.rglob("*.md"))
        if available:
            typer.echo("\nDid you mean one of these?")
            for f in sorted(available)[:5]:
                typer.echo(f"  {f.relative_to(canon_root)}")
        raise typer.Exit(1)

    try:
        content = target.read_text()
        typer.echo(content)
    except Exception as e:
        typer.echo(f"Error reading document: {e}", err=True)
        raise typer.Exit(1) from e
