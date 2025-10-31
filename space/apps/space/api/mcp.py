"""MCP management API."""

from space.lib.mcp import registry


def list_available_mcps() -> dict:
    """Return all available MCP definitions."""
    return registry.list_available()


def list_enabled_mcps() -> dict:
    """Return enabled MCPs in workspace."""
    return registry.get_launch_config()


def enable_mcp(name: str) -> None:
    """Enable MCP in workspace."""
    registry.enable(name)


def disable_mcp(name: str) -> None:
    """Disable MCP in workspace."""
    registry.disable(name)


def set_mcp_env(name: str, **kwargs) -> None:
    """Set environment variables for MCP."""
    registry.set_env(name, **kwargs)


def get_mcp_config(name: str) -> dict | None:
    """Get MCP configuration."""
    return registry.get_config(name)


__all__ = [
    "list_available_mcps",
    "list_enabled_mcps",
    "enable_mcp",
    "disable_mcp",
    "set_mcp_env",
    "get_mcp_config",
]
