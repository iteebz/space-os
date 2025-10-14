import typer

from ..lib.paths import canon_path

app = typer.Typer(help="Manage human's canonical values.")


@app.command(name="path")
def show_path():
    """Display the currently configured canon path."""
    typer.echo(f"Canon path: {canon_path()}")


@app.command(name="list")
def list_docs():
    """List all markdown documents within the configured canon path."""
    canon_root = canon_path()
    if not canon_root.exists():
        typer.echo(f"Canon path does not exist: {canon_root}")
        return

    md_files = list(canon_root.rglob("*.md"))
    if not md_files:
        typer.echo(f"No markdown documents found in {canon_root}")
        return

    typer.echo(f"Markdown documents in {canon_root}:")
    for md_file in md_files:
        typer.echo(f"  - {md_file.relative_to(canon_root)}")


@app.command(name="read")
def read_doc(
    document_name: str = typer.Argument(
        ..., help="Name of the document to read (e.g., 'space/meta.md')"
    ),
):
    """Display the content of a specific canon document."""
    canon_root = canon_path()
    doc_path = canon_root / document_name

    if not doc_path.exists():
        typer.echo(f"Document not found: {document_name} in {canon_root}")
        return

    typer.echo(doc_path.read_text())


def main() -> None:
    app()
