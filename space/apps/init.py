import contextlib
import time
from pathlib import Path

import typer

from space.lib import paths, store
from space.os import spawn
from space.os.spawn.api import symlinks

app = typer.Typer()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(init)


def archive_old_config():
    """Archive old provider config files with .old suffix."""
    old_configs = [
        Path.home() / ".claude" / "CLAUDE.md",
        Path.home() / ".gemini" / "GEMINI.md",
        Path.home() / ".codex" / "AGENTS.md",
    ]

    for old_path in old_configs:
        if old_path.exists():
            timestamp = int(time.time())
            new_path = old_path.parent / f"{old_path.stem}.{timestamp}.old"
            old_path.rename(new_path)
            typer.echo(f"✓ Archived {old_path.name} → {new_path.name}")


def init_default_agents():
    """Auto-discover and register agents from canon/constitutions/.

    Agents are created with identity matching constitution filename (without .md).
    """
    constitutions_dir = paths.canon_path() / "constitutions"
    if not constitutions_dir.exists():
        return

    constitution_files = sorted(constitutions_dir.glob("*.md"))
    if not constitution_files:
        return

    with spawn.db.connect():
        for const_file in constitution_files:
            if const_file.name == "README.md":
                continue
            identity = const_file.stem
            constitution = const_file.name

            with contextlib.suppress(ValueError):
                spawn.register_agent(identity, "claude-haiku-4-5", constitution)


@app.command()
def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.space_data().mkdir(parents=True, exist_ok=True)
    paths.canon_path().mkdir(parents=True, exist_ok=True)
    constitutions_dir = paths.canon_path() / "constitutions"
    constitutions_dir.mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    chats_dir = paths.chats_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)
    for cli in ["claude", "codex", "gemini"]:
        (chats_dir / cli).mkdir(exist_ok=True)

    spawn.db.register()

    with spawn.db.connect():
        pass
    with store.ensure("bridge"):
        pass
    with store.ensure("memory"):
        pass
    with store.ensure("knowledge"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data directory at {Path.home() / '.space'}")
    typer.echo(f"✓ Backup directory at {Path.home() / '.space_backups'}")

    archive_old_config()
    init_default_agents()

    bin_dir = Path.home() / ".local" / "bin"
    launch_script = paths.package_root().parent / "bin" / "launch"
    if launch_script.exists():
        bin_dir.mkdir(parents=True, exist_ok=True)
        if symlinks._setup_launch_symlink(launch_script):
            typer.echo("✓ Agent launcher configured (~/.local/bin/launch)")

    default_constitutions = ["zealot.md", "sentinel.md", "crucible.md"]
    
    typer.echo("✓ Default constitutions registered")

    typer.echo()
    typer.echo("Created space structure:")
    typer.echo("  ~/space/")
    typer.echo("    └── canon/                  → human curated context")
    typer.echo("        └── constitutions/      → identity prompts")
    for i, const_file in enumerate(default_constitutions):
        if i == len(default_constitutions) - 1:
            typer.echo(f"            ├── {const_file}")
        else:
            typer.echo(f"            ├── {const_file}")
    typer.echo("            └── (custom.md)")
    typer.echo()
    typer.echo("  ~/.space/")
    typer.echo("    ├── data/                   → runtime databases")
    typer.echo("    └── chats/                  → chat history")
    typer.echo()
    typer.echo("  ~/.space_backups/")
    typer.echo("    ├── data/                   → timestamped snapshots")
    typer.echo("    └── chats/                  → latest backup")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  1. Run: spawn agents")
    typer.echo("  2. Create a new *.md constitution file in ~/space/canon/constitutions/")
    typer.echo("  3. Register your agent: spawn register <identity> -m <model> -c <constitution>")


def main() -> None:
    """Entry point for poetry script."""
    app()
