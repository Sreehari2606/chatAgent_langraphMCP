"""
MCP Server - File & Code Execution Tools

Tools:
- read_file: Read file contents
- write_file: Write content to file  
- delete_file: Delete a file
- list_files: List files in directory
- run_python: Execute Python code
"""
from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("file-ops")


@mcp.tool()
def read_file(path: str) -> str:
    """Read and return the contents of a file"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file (creates or overwrites)"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File saved: {path}"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def delete_file(path: str) -> str:
    """Delete a file"""
    try:
        os.remove(path)
        return f"File deleted: {path}"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def list_files(directory: str) -> str:
    """List all files and folders in a directory as a tree"""
    try:
        result = []
        for root, dirs, files in os.walk(directory):
            level = root.replace(directory, '').count(os.sep)
            if level > 2:  # Limit depth
                continue
            indent = '    ' * level
            result.append(f"{indent}{os.path.basename(root)}/")
            subindent = '    ' * (level + 1)
            for f in files[:20]:  # Limit files
                result.append(f"{subindent}{f}")
        return "\n".join(result) or "Empty directory"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def run_python(code: str) -> str:
    """Execute Python code and return the output"""
    import io
    import sys
    
    # Capture stdout
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    
    try:
        exec(code, {"__builtins__": __builtins__})
        output = sys.stdout.getvalue()
        errors = sys.stderr.getvalue()
        
        result = output
        if errors:
            result += f"\nStderr:\n{errors}"
        return result or "Code executed (no output)"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


if __name__ == "__main__":
    mcp.run(transport="stdio")
