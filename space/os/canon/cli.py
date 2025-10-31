"""Canon CLI: Persistent Context (read-only, git-backed)."""

import typer

from space.lib import errors, output
from space.os.canon import api

errors.install_error_handler("canon")

app = typer.Typer(invoke_without_command=True, add_completion=False)


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def canon_callback(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format."),
    quiet_output: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-essential output."
    ),
):
    """Persistent context layer. Human's shared truth, immutable via git."""
    output.set_flags(ctx, json_output, quiet_output)
    if ctx.obj is None:
        ctx.obj = {}

    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command("tree")
def tree(
    ctx: typer.Context,
    path: str = typer.Argument(None, help="Path to show subtree (optional)"),
):
    """Show canon hierarchy as tree.

    Examples:
      canon tree                              # Show all paths
      canon tree research/safety              # Show research/safety subtree
    """
    tree_data = api.get_canon_entries()

    if path:
        parts = path.split("/")
        for part in parts:
            if part in tree_data:
                tree_data = tree_data[part]
            else:
                output.out_text(f"Path not found: {path}", ctx.obj)
                return

    def print_tree(node: dict, prefix: str = "", is_last: bool = True):
        items = list(node.items())
        for i, (key, subtree) in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "
            output.out_text(f"{prefix}{current_prefix}{key}", ctx.obj)
            next_prefix = prefix + ("    " if is_last_item else "│   ")
            if subtree:
                print_tree(subtree, next_prefix, is_last_item)

    if not tree_data:
        output.out_text("No canon documents found.", ctx.obj)
        return

    output.out_text("Canon hierarchy:", ctx.obj)
    print_tree(tree_data)


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    path: str = typer.Argument(
        ..., help="Path to inspect (e.g., architecture/caching or architecture/caching.md)"
    ),
):
    """View full canon document.

    Examples:
      canon inspect architecture/caching                   # View document
      canon inspect research/safety/cooperative-alignment  # View nested path
    """
    if not path:
        output.out_text("Path required", ctx.obj)
        return

    entry = api.read_canon(path)
    if not entry:
        output.out_text(f"Not found: {path}", ctx.obj)
        return

    if ctx.obj.get("json_output"):
        typer.echo(output.out_json({"path": entry.path, "content": entry.content}))
        return

    output.out_text(entry.content, ctx.obj)


def main() -> None:
    """Entry point for canon command."""
    try:
        app()
    except SystemExit:
        raise
    except BaseException as e:
        raise SystemExit(1) from e


__all__ = ["app", "main"]
