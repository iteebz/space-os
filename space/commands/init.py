from pathlib import Path

import typer

from space.core import chats, spawn
from space.lib import db, paths


def init():
    """Initialize space workspace structure and databases."""
    root = paths.space_root()

    paths.space_data().mkdir(parents=True, exist_ok=True)
    paths.canon_path().mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)

    with spawn.db.connect():
        pass
    with chats.db.connect():
        pass
    with db.ensure("bridge"):
        pass
    with db.ensure("memory"):
        pass
    with db.ensure("knowledge"):
        pass
    with db.ensure("events"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data at {Path.home() / '.space'}")

    # Register identities from config
    from space import config

    config.init_config()
    cfg = config.load_config()
    roles = cfg.get("roles", {})
    if roles:
        typer.echo("\nRegistering identities...")
        for role_name, role_cfg in roles.items():
            try:
                spawn.api.register_agent(
                    identity=role_name,
                    constitution=role_cfg["constitution"],
                    base_agent=role_cfg["base_agent"],
                )
                typer.echo(f"  + {role_name}")
            except ValueError:
                typer.echo(f"  = {role_name} (already registered)")
        typer.echo(f"\n✓ Registered {len(roles)} identities from config.")

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
