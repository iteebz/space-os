"""MCP registry and configuration API."""

import json

from space.lib import paths

MCP_FILE = paths.dot_space() / "mcp.json"


def list_available() -> dict:
    """Return all available MCP server definitions."""
    from space.lib.mcp import notion

    return {
        "notion": notion.DEFINITION,
    }


def load_config() -> dict:
    """Load .space/mcp.json or return empty dict."""
    if not MCP_FILE.exists():
        return {}
    try:
        return json.loads(MCP_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    """Write .space/mcp.json atomically."""
    MCP_FILE.parent.mkdir(parents=True, exist_ok=True)
    MCP_FILE.write_text(json.dumps(config, indent=2))


def enable(name: str) -> None:
    """Enable MCP in workspace."""
    available = list_available()
    if name not in available:
        raise ValueError(f"Unknown MCP: {name}")

    config = load_config()
    if name not in config:
        config[name] = available[name].copy()
    config[name]["enabled"] = True
    save_config(config)


def disable(name: str) -> None:
    """Disable MCP in workspace."""
    config = load_config()
    if name in config:
        config[name]["enabled"] = False
    save_config(config)


def set_env(name: str, **kwargs) -> None:
    """Set environment variables for MCP."""
    config = load_config()
    config.setdefault(name, {}).setdefault("env", {}).update(kwargs)
    save_config(config)


def get_launch_config() -> dict:
    """Return MCP config for agent launch (only enabled MCPs)."""
    config = load_config()
    return {k: v for k, v in config.items() if v.get("enabled")}


def get_config(name: str) -> dict | None:
    """Get config for specific MCP."""
    config = load_config()
    return config.get(name)


__all__ = [
    "list_available",
    "load_config",
    "save_config",
    "enable",
    "disable",
    "set_env",
    "get_launch_config",
    "get_config",
]
