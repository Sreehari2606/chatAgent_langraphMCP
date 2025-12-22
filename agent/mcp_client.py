"""
MCP Client using langchain_mcp_adapters - Proper MCP integration
"""
import os
from langchain_mcp_adapters.client import MultiServerMCPClient


MCP_SERVERS = {
    "file_ops": {
        "transport": "stdio",
        "command": "python",
        "args": [os.path.join(os.path.dirname(os.path.dirname(__file__)), "mymcp.py")],
    }
}


_client = None


async def get_mcp_client():
    """Get or create MCP client"""
    global _client
    if _client is None:
        _client = MultiServerMCPClient(MCP_SERVERS)
    return _client


async def get_mcp_tools():
    """Get all MCP tools as LangChain tools"""
    client = await get_mcp_client()
    return await client.get_tools()


async def call_mcp_tool_async(tool_name: str, **kwargs):
    """Call an MCP tool by name and return clean text output"""
    tools = await get_mcp_tools()
    for tool in tools:
        if tool.name == tool_name:
            try:
                result = await tool.ainvoke(kwargs)
                # Extract text from LangChain message structure
                if isinstance(result, list):
                    texts = []
                    for item in result:
                        if isinstance(item, dict) and 'text' in item:
                            texts.append(item['text'])
                    return ''.join(texts).strip()
                return str(result)
            except Exception as e:
                return f"ERROR: {e}"
    return f"ERROR: Tool '{tool_name}' not found"


def list_mcp_tools():
    """Return list of MCP tools for UI (consolidated source)"""
    return [
        {"name": "read_file", "description": "Read contents of a file", "params": ["path"]},
        {"name": "write_file", "description": "Write content to a file", "params": ["path", "content"]},
        {"name": "delete_file", "description": "Delete a file", "params": ["path"]},
        {"name": "list_files", "description": "List files in a directory", "params": ["directory"]},
        {"name": "run_python", "description": "Execute Python code", "params": ["code"]}
    ]


def _run_async(coro):
    """Run async coroutine in sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result(timeout=30)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def call_mcp_tool_sync(tool_name: str, **kwargs):
    """Sync bridge to call MCP tool"""
    try:
        return _run_async(call_mcp_tool_async(tool_name, **kwargs))
    except Exception as e:
        return f"ERROR: {e}"
