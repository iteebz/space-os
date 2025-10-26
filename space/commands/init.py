from pathlib import Path

import typer

from space.core import chats, spawn
from space.core.spawn import api
from space.lib import paths, store


def init_default_agents():
    """Register default agents from config, replacing old role-based system."""
    from space import config

    config.init_config()
    cfg = config.load_config()
    roles = cfg.get("roles", {})

    if not roles:
        return

    typer.echo("\nRegistering identities...")
    count = 0

    for role_name, role_cfg in roles.items():
        try:
            provider = role_cfg.get("provider")
            model = role_cfg.get("model")

            if not provider or not model:
                config_agents = cfg.get("agents", {})
                base_agent = role_cfg.get("base_agent")
                if base_agent and base_agent in config_agents:
                    base_cfg = config_agents[base_agent]
                    provider = _map_command_to_provider(base_cfg.get("command", base_agent))
                    model = base_cfg.get("model")

            if not provider or not model:
                typer.echo(f"  ⚠ {role_name} missing provider/model, skipping")
                continue

            api.register_agent(
                identity=role_name,
                constitution=role_cfg["constitution"],
                provider=provider,
                model=model,
            )
            typer.echo(f"  + {role_name}")
            count += 1
        except ValueError:
            typer.echo(f"  = {role_name} (already registered)")

    if count > 0:
        typer.echo(f"\n✓ Registered {count} identities from config.")


def _map_command_to_provider(command: str) -> str:
    """Map provider command to provider name."""
    cmd_map = {
        "claude": "claude",
        "gemini": "gemini",
        "codex": "codex",
    }
    base_cmd = command.split()[0] if isinstance(command, str) else command[0]
    return cmd_map.get(base_cmd, base_cmd)


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
    with store.ensure("bridge"):
        pass
    with store.ensure("memory"):
        pass
    with store.ensure("knowledge"):
        pass
    with store.ensure("events"):
        pass

    typer.echo(f"✓ Initialized workspace at {root}")
    typer.echo(f"✓ User data at {Path.home() / '.space'}")

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
