import contextlib
import time
from pathlib import Path

import typer

from space.core import chats, spawn
from space.lib import paths, store


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
    """Register default agents with correct providers."""
    default_agents = [
        ("zealot", "zealot.md", "claude", "claude-haiku-4-5"),
        ("crucible", "crucible.md", "gemini", "gemini-2.0-flash"),
        ("sentinel", "sentinel.md", "codex", "codex-latest"),
    ]

    with spawn.db.connect():
        for identity, constitution, provider, model in default_agents:
            with contextlib.suppress(ValueError):
                spawn.register_agent(identity, constitution, provider, model)


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
    chats.db.register()

    with spawn.db.connect():
        pass
    with chats.db.connect():
        pass
    with store.ensure("bridge"):
        pass
    with store.ensure("memory"):
        pass
    with store.ensure("knowledge"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data at {Path.home() / '.space'}")

    archive_old_config()
    init_default_agents()

    typer.echo()
    typer.echo("  ~/space/")
    typer.echo("    ├── canon/      → your persistent context (edit here)")
    typer.echo("    └── (code)")
    typer.echo()
    typer.echo("  ~/.space/")
    typer.echo("    ├── data/       → runtime databases")
    typer.echo("    └── backups/    → snapshots")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  space wake --as <identity>")
