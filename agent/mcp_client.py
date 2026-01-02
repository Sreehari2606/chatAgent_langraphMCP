"""MCP Client"""
import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "file_ops": {
            "transport": "stdio",
            "command": "python",
            "args": [os.path.join(os.path.dirname(os.path.dirname(__file__)), "mymcp.py")],
        }
    }
)


async def get_tools():
    return await client.get_tools()


async def call_mcp_tool(tool_name: str, **kwargs):
    tools = await get_tools()
    for tool in tools:
        if tool.name == tool_name:
            result = await tool.ainvoke(kwargs)
            if isinstance(result, list):
                return ''.join(item.get('text', '') for item in result if isinstance(item, dict)).strip()
            return str(result)
    return f"Tool '{tool_name}' not found"


def call_mcp_tool_sync(tool_name: str, **kwargs):
    return asyncio.run(call_mcp_tool(tool_name, **kwargs))


def list_mcp_tools():
    return [
        {"name": "read_file", "description": "Read contents of a file", "params": ["path"]},
        {"name": "write_file", "description": "Write content to a file", "params": ["path", "content"]},
        {"name": "delete_file", "description": "Delete a file", "params": ["path"]},
        {"name": "list_files", "description": "List files in a directory", "params": ["directory"]},
        {"name": "run_python", "description": "Execute Python code", "params": ["code"]}
    ]
