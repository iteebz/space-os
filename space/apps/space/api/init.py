import contextlib
import os
import time
from pathlib import Path

import typer

from space.lib import paths, store
from space.os import sessions, spawn
from space.os.spawn import defaults as spawn_defaults

app = typer.Typer()


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        ctx.invoke(init)


def archive_old_config():
    """Archive old provider config files with .old suffix.

    Only archives if content doesn't match default constitutions to avoid spam.
    """
    default_constitutions = ["zealot.md", "sentinel.md", "crucible.md"]
    old_configs = [
        Path.home() / ".claude" / "CLAUDE.md",
        Path.home() / ".gemini" / "GEMINI.md",
        Path.home() / ".codex" / "AGENTS.md",
    ]

    constitutions_dir = paths.canon_path() / "constitutions"

    for old_path in old_configs:
        if not old_path.exists():
            continue

        old_content = old_path.read_text()
        is_default = False

        for const_name in default_constitutions:
            const_file = constitutions_dir / const_name
            if const_file.exists() and const_file.read_text() == old_content:
                is_default = True
                break

        if not is_default:
            timestamp = int(time.time())
            new_path = old_path.parent / f"{old_path.stem}.{timestamp}.old"
            old_path.rename(new_path)
            typer.echo(f"✓ Archived {old_path.name} → {new_path.name}")


def init_default_agents():
    """Auto-discover and register agents from canon/constitutions/.

    Agents are created with identity matching constitution filename (without .md).
    Also registers 'human' as a reserved identity for bridge communication.
    """
    constitutions_dir = paths.canon_path() / "constitutions"
    if not constitutions_dir.exists():
        return

    constitution_files = sorted(constitutions_dir.glob("*.md"))
    if not constitution_files:
        return

    with store.ensure():
        with contextlib.suppress(ValueError):
            spawn.register_agent("human", "human", None)

        for const_file in constitution_files:
            if const_file.name == "README.md":
                continue
            identity = const_file.stem
            constitution = identity

            with contextlib.suppress(ValueError):
                model = spawn_defaults.canonical_model(identity)
                spawn.register_agent(identity, model, constitution)


def _get_bin_dir() -> Path:
    """Get ~/.local/bin directory."""
    return Path.home() / ".local" / "bin"


def _list_agent_identities() -> list[str]:
    """Get all registered agent identities from spawn DB."""
    with store.ensure():
        agents = spawn.api.list_agents()
    return [agent.identity for agent in agents]


def _is_bin_in_path() -> bool:
    """Check if ~/.local/bin is in PATH."""
    bin_dir = str(_get_bin_dir())
    return bin_dir in os.getenv("PATH", "")


def _install_shortcuts():
    """Install identity shortcuts in ~/.local/bin."""
    bin_dir = _get_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)

    identities = _list_agent_identities()
    if not identities:
        return

    for identity in identities:
        script_path = bin_dir / identity
        script_content = f'#!/usr/bin/env bash\nexec spawn {identity} "$@"\n'
        script_path.write_text(script_content)
        script_path.chmod(0o755)

    typer.echo(f"✓ Installed {len(identities)} identity shortcuts")
    if not _is_bin_in_path():
        typer.echo('⚠ Add to PATH: export PATH="$HOME/.local/bin:$PATH"')


@app.command()
def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.canon_path().mkdir(parents=True, exist_ok=True)
    constitutions_dir = paths.canon_path() / "constitutions"
    constitutions_dir.mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    sessions_dir = paths.sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    for cli in ["claude", "codex", "gemini"]:
        (sessions_dir / cli).mkdir(exist_ok=True)

    with store.ensure():
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data directory at {Path.home() / '.space'}")
    typer.echo(f"✓ Backup directory at {Path.home() / '.space_backups'}")

    archive_old_config()
    init_default_agents()

    constitutions_dir = paths.canon_path() / "constitutions"
    constitution_files = sorted(
        [f.name for f in constitutions_dir.glob("*.md") if f.name != "README.md"]
    )
    typer.echo(f"✓ {len(constitution_files)} constitutions registered")

    from space.cli import output

    typer.echo("Syncing provider sessions...")
    typer.echo(f"  {'Provider':<10} {'Discovered':<12} {'Synced'}")

    sessions.api.sync.sync_all(on_progress=output.show_sync_progress)

    _install_shortcuts()

    typer.echo()
    typer.echo("Created space structure:")
    typer.echo("  ~/space/")
    typer.echo("    └── canon/                  → human curated context")
    typer.echo("        └── constitutions/      → identity prompts")
    for i, const_file in enumerate(constitution_files):
        if i == len(constitution_files) - 1:
            typer.echo(f"            └── {const_file}")
        else:
            typer.echo(f"            ├── {const_file}")
    typer.echo()
    typer.echo("  ~/.space/")
    typer.echo("    ├── sync.json               → session sync state")
    typer.echo("    └── sessions/               → provider session history")
    typer.echo()
    typer.echo("  ~/.space_backups/")
    typer.echo("    ├── data/                   → timestamped snapshots")
    typer.echo("    └── sessions/               → latest backup")

    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  1. Create a new *.md constitution file in ~/space/canon/constitutions/")
    typer.echo("  2. Register your agent: spawn register <identity> -m <model> -c <constitution>")


def main() -> None:
    """Entry point for poetry script."""
    app()
