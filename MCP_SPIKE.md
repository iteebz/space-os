# MCP Integration Spike: Wedding Notion Agent

## Executive Summary

**Feasible and Low-Friction.** MCP (Model Context Protocol) can be integrated into space-os agents with minimal changes to the existing launch pipeline. Both Claude and Codex CLIs natively support `--mcp-config`, making integration straightforward.

## What We Found

### 1. Provider CLI Support
- **Claude**: `--mcp-config <file or string>` — loads MCP servers from JSON file or inline string
- **Codex**: `codex mcp` subcommand (experimental) + `--mcp-config` support on roadmap
- **Gemini**: No current MCP support (Gemini CLI doesn't expose tool framework)

### 2. MCP Architecture
```
Host (Agent)
    ↓
MCP Server (Notion)
    ↓
External Service (Notion API)
```

MCP uses **JSON-RPC over stdio** for local connections. Servers expose:
- **Tools**: Executable functions (read/write tasks, update properties, etc.)
- **Resources**: Read-only data (@-mentionable context)
- **Prompts**: Pre-written interaction templates

### 3. Integration Points

#### Option A: Dynamic MCP Config in Launch Pipeline (Recommended)
Modify `space/os/spawn/api/main.py:spawn_agent()`:

```python
def spawn_agent(identity: str, extra_args: list[str] | None = None):
    agent = agents.get_agent(identity)
    
    # Load MCP servers for this agent from config
    mcp_config = _load_mcp_config(agent)
    
    # Pass to provider via --mcp-config
    mcp_args = ["--mcp-config", json.dumps(mcp_config)] if mcp_config else []
    
    full_command = command_tokens + model_args + mcp_args + passthrough
    # ... rest of spawn
```

Agent config could specify:
```python
# In agent metadata or constitution
mcp_servers: {
    "notion": {
        "command": "notion-mcp-server",
        "args": ["--workspace-id", "..."]
    }
}
```

#### Option B: Environment-Based Discovery
Load MCP servers from standard locations:
- `~/.claude/mcp-servers.json` (Claude Desktop convention)
- `~/.codex/mcp-servers.json`
- Project-local `.space/mcp-servers.json`

#### Option C: Bridge as MCP Relay
Expose bridge channels as MCP resources:
- `@bridge://general` → read unread messages
- `@bridge://wedding-planning` → context for planning tasks

Agents could query Notion → post results to bridge → other agents consume via MCP resources.

## Notion MCP Server Design

### Tool Schema (Wedding Planning Example)

```json
{
  "name": "wedding-notion-tools",
  "tools": [
    {
      "name": "query_tasks",
      "description": "Get wedding tasks by status (Todo, In Progress, Done)",
      "inputSchema": {
        "type": "object",
        "properties": {
          "status": { "type": "string", "enum": ["Todo", "In Progress", "Done"] },
          "assignee": { "type": "string", "description": "Filter by assignee name" }
        },
        "required": ["status"]
      }
    },
    {
      "name": "create_task",
      "description": "Create a new wedding task",
      "inputSchema": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "status": { "type": "string", "enum": ["Todo", "In Progress", "Done"] },
          "assignee": { "type": "string" },
          "dueDate": { "type": "string", "format": "date" },
          "description": { "type": "string" }
        },
        "required": ["title", "status"]
      }
    },
    {
      "name": "update_task",
      "description": "Update existing task",
      "inputSchema": {
        "type": "object",
        "properties": {
          "taskId": { "type": "string" },
          "status": { "type": "string" },
          "assignee": { "type": "string" },
          "dueDate": { "type": "string", "format": "date" }
        },
        "required": ["taskId"]
      }
    },
    {
      "name": "list_vendors",
      "description": "List wedding vendors (catering, venue, etc.)",
      "inputSchema": {
        "type": "object",
        "properties": {
          "category": { "type": "string", "enum": ["Catering", "Venue", "Photography", "Music"] }
        }
      }
    }
  ]
}
```

### Implementation Path

1. **Create MCP server** (Python or TypeScript)
   - Use `fastmcp` (Python) or `@modelcontextprotocol/sdk` (TypeScript)
   - Authenticate with Notion API via environment variable or config
   - Implement tool handlers for CRUD operations

2. **Package as installable binary or script**
   - `pip install notion-mcp-server` or `npm install -g notion-mcp-server`
   - Or keep local in `.space/mcp/notion-server.py`

3. **Reference in agent launch**
   ```python
   mcp_servers = {
       "notion": {
           "command": "python",
           "args": ["/path/to/notion-mcp-server.py"],
           "env": {
               "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
               "NOTION_DATABASE_ID": "..."
           }
       }
   }
   ```

4. **Test with agents**
   - Create a `wedding-planner` agent with Notion MCP
   - Verify `claude --mcp-config {...}` can access tools
   - Build multi-agent workflows: task creation, status updates, vendor tracking

## Integration Effort Estimate

| Component | Effort | Notes |
|-----------|--------|-------|
| MCP config in spawn pipeline | 2-3 hours | Modify `main.py`, add agent metadata schema |
| Notion MCP server (POC) | 4-6 hours | Basic CRUD, error handling, token management |
| Agent constitution updates | 1 hour | Add Notion context to wedding planner agent |
| Testing + multi-agent coordination | 2-3 hours | Test task creation, bridge messaging, consensus |
| **Total** | **9-13 hours** | Full spike implementation |

## Recommendations

### 🎯 Start Here (Next Steps)

1. **Create simple Notion MCP server** (TypeScript or Python)
   - Use `fastmcp` or official SDK
   - 3-4 core tools: query_tasks, create_task, update_task, list_vendors
   - Local test: `notion-mcp-server --api-key=... --db-id=...`

2. **Patch main.py** to pass `--mcp-config`
   - Keep it simple: read from agent metadata or environment
   - No distributed state needed for MVP

3. **Create wedding-planner agent**
   - Constitution: focuses on task coordination, vendor selection
   - Add to constitution: "You have access to wedding Notion database via MCP tools"
   - Test: `spawn wedding-planner "Create task: confirm catering date"`

4. **Build multi-agent workflow**
   - Agent A (planner): creates tasks via MCP
   - Agent B (coordinator): polls bridge for updates, posts summaries
   - Notion becomes shared state across agents

### 🚀 Why This Works

- **Zero breaking changes** — MCP is purely additive, `--mcp-config` already exists
- **Decoupled** — Notion integration lives in separate MCP server, not in space-os
- **Composable** — Can add other MCP servers (GitHub, Slack, Cal.com) later
- **Agent-specific** — Each agent can have different MCP configs (wedding planner ≠ devops agent)

### ⚠️ Design Notes

1. **State Management**: Notion becomes source of truth for wedding state. Bridge can be used for inter-agent coordination (poll frequency, conflict resolution).

2. **Error Handling**: MCP server should retry transient Notion API errors. Agent constitution should handle tool failures gracefully.

3. **Authentication**: Store `NOTION_API_KEY` in environment, not constitution (security).

4. **Multi-Agent Safety**: If multiple agents modify tasks simultaneously, use Notion's last-write-wins or implement locking in bridge layer.

## Files to Modify

```
space/os/spawn/api/main.py          # Add --mcp-config support
space/os/spawn/models.py              # Add mcp_servers field to Agent model
space/os/spawn/constitutions/         # Add wedding-planner.md
```

## Proof of Concept: Minimal Test

```bash
# 1. Start Notion MCP server
python notion-mcp-server.py --api-key=$NOTION_API_KEY --db-id=$DB_ID

# 2. Launch agent with MCP config
claude \
  --mcp-config '{"servers": {"notion": {"command": "python", "args": ["notion-mcp-server.py"]}}}' \
  "List all todo tasks and summarize"

# 3. Agent can now:
# - Call query_tasks tool → get Notion data
# - Call create_task tool → add new wedding task
# - Coordinate with other agents via bridge
```

## Conclusion

**MCP integration is low-friction and aligns with space-os philosophy** (composable primitives, no cloud dependencies, workspace sovereignty). The Notion wedding agent becomes a first-class citizen in your swarm, with access to both bridge coordination and external state via MCP tools.

Ready to build? Start with the Notion MCP server, then patch main.py.
