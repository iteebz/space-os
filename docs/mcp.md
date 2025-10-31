# MCP Integration: External State Access

MCP (Model Context Protocol) enables agents to access external APIs and data sources via standardized tools.

## Architecture

```
Agent (spawn launch <agent>)
    ↓
MCP Config (from ~/.space/mcp.json)
    ↓
MCP Server (e.g., Notion)
    ↓
External Service (Notion API, GitHub, etc.)
```

MCP servers expose **tools** (executable functions) that agents can call. Each tool has:
- `name`: Identifier (e.g., `query_tasks`)
- `description`: Human-readable explanation
- `inputSchema`: JSON Schema for tool parameters

## Usage

### Enable an MCP Server

```bash
space mcp list                    # View available MCPs
space mcp enable notion           # Enable Notion integration
space mcp config notion           # Set API credentials
```

This writes to `~/.space/mcp.json`:
```json
{
  "notion": {
    "name": "notion",
    "enabled": true,
    "command": "python",
    "args": ["-m", "space.lib.mcp.servers.notion"],
    "env": {
      "NOTION_API_KEY": "...",
      "NOTION_DB_ID": "..."
    }
  }
}
```

### Launch Agent with MCP

```bash
spawn launch wedding-planner "List all tasks"
```

The agent receives `--mcp-config` automatically via the spawn launch pipeline and can call enabled MCP tools.

## Creating New MCP Servers

Add a new server file in `space/lib/mcp/<service>.py`:

```python
DEFINITION = {
    "name": "github",
    "description": "Query GitHub repositories",
    "command": "python",
    "args": ["-m", "space.lib.mcp.github"],
    "required_env": ["GITHUB_TOKEN"],
}

async def run_server():
    """Run GitHub MCP server using fastmcp."""
    from fastmcp.server import Server
    
    server = Server("github")
    
    @server.list_tools()
    async def list_tools():
        return [
            {
                "name": "search_repos",
                "description": "Search GitHub repositories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "search_repos":
            # Implement GitHub API call
            ...
    
    async with server.stdio_transport() as transport:
        await server.run(transport)

if __name__ == "__main__":
    asyncio.run(run_server())
```

Then register it in `space/lib/mcp/registry.py`:

```python
def list_available() -> dict:
    from space.lib.mcp import notion, github
    return {
        "notion": notion.DEFINITION,
        "github": github.DEFINITION,
    }
```

## Implementation Details

### Registry (`space/lib/mcp/registry.py`)

Core API for managing MCP configurations:
- `list_available()` — List all defined MCPs
- `enable(name)` — Enable MCP in workspace
- `disable(name)` — Disable MCP
- `set_env(name, **kwargs)` — Configure API credentials
- `get_launch_config()` — Get enabled MCPs for agent launch

### Agent Launch Integration (`space/os/spawn/api/prompt.py`)

When spawning an agent, the launch pipeline:
1. Loads enabled MCPs via `registry.get_launch_config()`
2. Builds `--mcp-config` JSON for the provider CLI
3. Passes to Claude/Codex with: `claude --mcp-config '{"servers": {...}}' ...`

### CLI (`space/apps/space/cli.py`)

User-facing commands under `space mcp`:
- `space mcp list` — Show available and enabled MCPs
- `space mcp enabled` — Show currently enabled MCPs
- `space mcp enable <name>` — Enable an MCP
- `space mcp disable <name>` — Disable an MCP
- `space mcp config <name>` — Set API credentials

## Design Principles

1. **Workspace-scoped**: Configurations stored in `~/.space/mcp.json`, not per-agent
2. **External state only**: MCP is for APIs outside the local environment. Coordination via bridge.
3. **Read-first**: Start with read-only tools (query_tasks). Write operations are future scope.
4. **Composable**: Easy to add new MCP servers without modifying space-os core.
5. **Security**: API keys stored in environment, never in constitution or code.

## Example: Notion Wedding Planning

See `space/lib/mcp/notion.py` for a complete example:

```bash
# 1. Get Notion API key from https://www.notion.so/my-integrations
# 2. Get database ID from Notion URL: notion.so/<workspace>/<database-id>
# 3. Enable and configure
space mcp enable notion
space mcp config notion

# 4. Launch agent with access to wedding tasks
spawn launch wedding-planner "Show all tasks due this week"
```

The agent calls `query_tasks(status="Todo")` to retrieve tasks from Notion, then acts on the results.
