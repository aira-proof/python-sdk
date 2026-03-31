"""MCP server exposing Aira actions as tools for AI agents."""
from __future__ import annotations
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
except ImportError:
    raise ImportError(
        "mcp is required for the MCP server integration. "
        "Install with: pip install aira-sdk[mcp]"
    )


def create_server(api_key: str | None = None, base_url: str | None = None) -> Server:
    """Create an MCP server with Aira tools."""
    from aira import Aira

    key = api_key or os.environ.get("AIRA_API_KEY", "")
    if not key:
        raise ValueError("API key required — pass api_key or set AIRA_API_KEY")

    kwargs: dict[str, Any] = {"api_key": key}
    if base_url:
        kwargs["base_url"] = base_url

    client = Aira(**kwargs)
    server = Server("aira")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="notarize_action",
                description="Notarize an AI agent action with a cryptographic receipt",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string", "description": "e.g. email_sent, loan_approved, claim_processed"},
                        "details": {"type": "string", "description": "What happened"},
                        "agent_id": {"type": "string", "description": "Agent slug"},
                        "model_id": {"type": "string", "description": "Model used (optional)"},
                    },
                    "required": ["action_type", "details"],
                },
            ),
            Tool(
                name="verify_action",
                description="Verify a notarized action's cryptographic receipt",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "string", "description": "Action UUID"},
                    },
                    "required": ["action_id"],
                },
            ),
            Tool(
                name="get_receipt",
                description="Get the cryptographic receipt for a notarized action",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "receipt_id": {"type": "string", "description": "Receipt UUID"},
                    },
                    "required": ["receipt_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "notarize_action":
                result = client.notarize(**{k: v for k, v in arguments.items() if v})
                data = result.__dict__ if hasattr(result, "__dict__") else result
                return [TextContent(type="text", text=json.dumps(data, default=str))]
            elif name == "verify_action":
                result = client.verify_action(arguments["action_id"])
                data = result.__dict__ if hasattr(result, "__dict__") else result
                return [TextContent(type="text", text=json.dumps(data, default=str))]
            elif name == "get_receipt":
                result = client.get_receipt(arguments["receipt_id"])
                data = result.__dict__ if hasattr(result, "__dict__") else result
                return [TextContent(type="text", text=json.dumps(data, default=str))]
            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


def main():
    """Entry point for aira-mcp console script."""
    import asyncio
    from mcp.server.stdio import stdio_server

    server = create_server()

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)

    asyncio.run(run())


if __name__ == "__main__":
    main()
