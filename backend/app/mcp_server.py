"""
Grayn AEO — MCP Server

Exposes AEO visibility data to Claude Desktop and Cursor via Model Context Protocol.
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from typing import Any
import json
import logging
from mcp.server import Server
import mcp.types as types
from mcp.server.sse import SseServerTransport

logger = logging.getLogger(__name__)

server = Server("grayn-aeo-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available AEO tracking tools."""
    return [
        types.Tool(
            name="get_visibility_report",
            description="Get the AI visibility report for a workspace for a specific week",
            inputSchema={
                "type": "object",
                "properties": {
                    "iso_week": {
                        "type": "string",
                        "description": "ISO week (e.g., 2026-W23)"
                    }
                },
                "required": ["iso_week"]
            }
        ),
        types.Tool(
            name="list_workstreams",
            description="List all tracked AEO workstreams",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="get_recommendations",
            description="Get AI-generated SEO/AEO recommendations to improve brand visibility",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Execute AEO tool."""
    from app.database import get_supabase
    
    db = get_supabase()
    # Assume single workspace for MCP context
    workspace_data = db.table("workspaces").select("id").limit(1).execute()
    if not workspace_data.data:
        return [types.TextContent(type="text", text="Error: No workspace found.")]
    
    workspace_id = workspace_data.data[0]["id"]
    
    try:
        if name == "get_visibility_report":
            iso_week = arguments.get("iso_week")
            if not iso_week:
                return [types.TextContent(type="text", text="Missing iso_week argument.")]
            
            runs = db.table("aeo_runs").select("engine, status, cost_usd").eq("workspace_id", workspace_id).eq("iso_week", iso_week).execute().data
            return [types.TextContent(type="text", text=json.dumps({"iso_week": iso_week, "runs_count": len(runs), "runs": runs}, indent=2))]
            
        elif name == "list_workstreams":
            ws = db.table("aeo_workstreams").select("name, target_visibility, topics, attribute_filters").eq("workspace_id", workspace_id).execute().data
            return [types.TextContent(type="text", text=json.dumps(ws, indent=2))]
            
        elif name == "get_recommendations":
            recs = db.table("aeo_recommendations").select("content, engine, status").eq("workspace_id", workspace_id).execute().data
            return [types.TextContent(type="text", text=json.dumps(recs, indent=2))]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.exception(f"MCP Tool error: {e}")
        return [types.TextContent(type="text", text=f"Tool Execution Failed: {str(e)}")]

# FastAPI Router integration
router = APIRouter()
sse = SseServerTransport("/mcp/messages")

@router.get("/mcp")
async def handle_sse(request: Request):
    """MCP SSE endpoint."""
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )

@router.post("/mcp/messages")
async def handle_messages(request: Request):
    """MCP POST messages endpoint."""
    await sse.handle_post_message(request.scope, request.receive, request._send)
