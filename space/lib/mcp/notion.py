"""Notion MCP server definition and handler.

To use this with a real Notion database:

1. Create a Notion integration: https://www.notion.so/my-integrations
   - Copy the API key (secret)

2. Get your database ID from the Notion URL:
   - URL: https://notion.so/<workspace>/<database-id>?v=<view-id>
   - Extract: <database-id>

3. Enable and configure:
   $ space mcp enable notion
   $ space mcp config notion
   - Enter NOTION_API_KEY (from step 1)
   - Enter NOTION_DB_ID (from step 2)

4. Launch an agent:
   $ spawn launch wedding-planner "List all Todo tasks"

   The agent will have access to notion.query_tasks tool.
"""

import asyncio
import json
import os

DEFINITION = {
    "name": "notion",
    "description": "Query Notion databases",
    "command": "python",
    "args": ["-m", "space.lib.mcp.servers.notion"],
    "required_env": ["NOTION_API_KEY", "NOTION_DB_ID"],
}


async def run_server():
    """Run Notion MCP server (fastmcp-based).

    Requires: fastmcp, notion-client
    Environment: NOTION_API_KEY, NOTION_DB_ID
    """
    try:
        from fastmcp.server import Server
        from notion_client import Client
    except ImportError:
        print(
            "Error: fastmcp and notion-client required. Install: pip install fastmcp notion-client"
        )
        return

    api_key = os.getenv("NOTION_API_KEY")
    db_id = os.getenv("NOTION_DB_ID")

    if not api_key or not db_id:
        print("Error: NOTION_API_KEY and NOTION_DB_ID environment variables required")
        return

    server = Server("notion")
    notion = Client(auth=api_key)

    @server.list_tools()
    async def list_tools():
        return [
            {
                "name": "query_tasks",
                "description": "Get wedding tasks by status (Todo, In Progress, Done)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["Todo", "In Progress", "Done"],
                            "description": "Filter by task status",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Optional filter by assignee name",
                        },
                    },
                    "required": ["status"],
                },
            },
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "query_tasks":
                status = arguments.get("status")
                assignee_filter = arguments.get("assignee")

                query = {
                    "database_id": db_id,
                    "filter": {
                        "property": "Status",
                        "status": {"equals": status},
                    },
                }

                results = notion.databases.query(**query)
                tasks = []
                for page in results["results"]:
                    task_data = {
                        "id": page["id"],
                        "title": page["properties"]
                        .get("Name", {})
                        .get("title", [{}])[0]
                        .get("text", {})
                        .get("content", ""),
                        "status": page["properties"]
                        .get("Status", {})
                        .get("status", {})
                        .get("name", ""),
                        "assignee": page["properties"]
                        .get("Assignee", {})
                        .get("people", [{}])[0]
                        .get("name", "")
                        if page["properties"].get("Assignee", {}).get("people")
                        else None,
                    }
                    if assignee_filter is None or task_data["assignee"] == assignee_filter:
                        tasks.append(task_data)

                return json.dumps({"tasks": tasks})

            return json.dumps({"error": f"Unknown tool: {name}"})

        except Exception as e:
            return json.dumps({"error": str(e)})

    async with server.stdio_transport() as transport:
        await server.run(transport)


if __name__ == "__main__":
    asyncio.run(run_server())
