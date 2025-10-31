"""MCP management API (delegated to lib.mcp.registry)."""

from space.lib.mcp.registry import (
    disable,
    enable,
    get_config,
    get_launch_config,
    list_available,
    set_env,
)

list_available_mcps = list_available
list_enabled_mcps = get_launch_config
enable_mcp = enable
disable_mcp = disable
set_mcp_env = set_env
get_mcp_config = get_config

__all__ = [
    "list_available_mcps",
    "list_enabled_mcps",
    "enable_mcp",
    "disable_mcp",
    "set_mcp_env",
    "get_mcp_config",
]
