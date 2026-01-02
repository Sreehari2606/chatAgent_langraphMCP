"""
WillOfCode: Specialized Agents
Each agent is a mini-graph with its own expertise
"""
from agent.state import WillOfCodeState
from agent.llm import llm_invoke, llm_invoke_json
from agent.mcp_client import call_mcp_tool_sync, list_mcp_tools


# ============================================================================
# CODER AGENT - Generates and edits code
# ============================================================================
def coder_agent(state: WillOfCodeState) -> WillOfCodeState:
    """Handles code generation, editing, and creation tasks"""
    query = state["user_query"]
    file_content = state.get("file_content", "")
    file_path = state.get("file_path", "")
    
    # Check if this is an edit request (has existing file content)
    is_edit = bool(file_content)
    
    if is_edit:
        # Editing existing code - use JSON format for structured response
        prompt = f"""You are editing a file. Make ONLY the requested change.
CRITICAL: Return the COMPLETE file content with your modification applied.
Do NOT omit any existing code - include EVERY line from the original file.

Return JSON format:
{{"modified_code": "THE COMPLETE FILE WITH ALL ORIGINAL LINES PLUS YOUR CHANGE", "changes": "brief description of what you changed"}}

User request: {query}

COMPLETE ORIGINAL FILE:
```
{file_content}
```

Remember: Return the ENTIRE file content, not just the changed parts."""
        
        result = llm_invoke_json(prompt)
        code = result.get("modified_code", "")
        changes = result.get("changes", "Code modified")
        llm_result = f"## Changes Made\n\n{changes}\n\n*Review the changes in the editor and click Accept to apply*"
        
        # Set pending action for frontend to show diff
        pending_action = "stream_to_editor"
        action_data = {
            "type": "file_edit",
            "code": code,
            "path": file_path,
            "changes": changes,
            "original": file_content
        }
    else:
        # Generating new code
        prompt = f"""You are an expert Code Generation Agent.
Your specialty is writing clean, efficient, and well-documented code.

User Request: {query}

Instructions:
- Generate high-quality code that solves the user's request
- Include helpful comments
- Follow best practices for the language

Provide your response:"""
        
        result = llm_invoke(prompt)
        llm_result = result.get("generate", "Error generating code")
        pending_action = None
        action_data = None
        code = ""
    
    # Update agent tracking
    history = state.get("agent_history", []) or []
    history.append("coder")
    
    outputs = state.get("agent_outputs", {}) or {}
    outputs["coder"] = code if is_edit else llm_result
    
    return {
        **state,
        "current_agent": "coder",
        "agent_history": history,
        "agent_outputs": outputs,
        "llm_result": llm_result,
        "pending_action": pending_action,
        "action_data": action_data,
        "code": code if code else None
    }


# ============================================================================
# REVIEWER AGENT - Reviews and refactors code
# ============================================================================
def reviewer_agent(state: WillOfCodeState) -> WillOfCodeState:
    """Handles code review, refactoring, and quality improvements"""
    query = state["user_query"]
    query_lower = query.lower()
    file_content = state.get("file_content", "")
    file_path = state.get("file_path", "")
    code = state.get("code", file_content)
    
    # Check if this is a refactor/optimize request with existing code
    is_refactor = any(kw in query_lower for kw in ["refactor", "optimize", "improve", "clean"])
    has_code = bool(code)
    
    if is_refactor and has_code:
        # Refactoring - use JSON format for structured response
        prompt = f"""You are refactoring code. Return the COMPLETE refactored file.

Return JSON format:
{{"refactored_code": "THE COMPLETE REFACTORED CODE", "changes": ["change1", "change2"]}}

User request: {query}

ORIGINAL CODE:
```
{code}
```"""
        
        result = llm_invoke_json(prompt)
        refactored = result.get("refactored_code", "")
        changes = result.get("changes", [])
        changes_text = "\n".join(f"- {c}" for c in changes) if isinstance(changes, list) else str(changes)
        llm_result = f"## Refactored Code\n\n**Changes:**\n{changes_text}\n\n*Review the changes in the editor and click Accept to apply*"
        
        pending_action = "stream_to_editor"
        action_data = {
            "type": "refactor",
            "code": refactored,
            "path": file_path,
            "changes": changes_text,
            "original": code
        }
    else:
        # Code review only (no refactoring)
        prompt = f"""You are an expert Code Review Agent.
Your specialty is analyzing code quality and suggesting improvements.

User Request: {query}

Code to Review:
{code if code else "No code provided for review."}

Instructions:
- Analyze code quality, readability, and maintainability
- Identify potential bugs or issues
- Suggest specific improvements with examples
- Rate the code quality (1-10)

Provide your detailed review:"""
        
        result = llm_invoke(prompt)
        llm_result = result.get("generate", "Error reviewing code")
        pending_action = None
        action_data = None
        refactored = ""
    
    history = state.get("agent_history", []) or []
    history.append("reviewer")
    
    outputs = state.get("agent_outputs", {}) or {}
    outputs["reviewer"] = refactored if is_refactor else llm_result
    
    return {
        **state,
        "current_agent": "reviewer",
        "agent_history": history,
        "agent_outputs": outputs,
        "llm_result": llm_result,
        "pending_action": pending_action,
        "action_data": action_data,
        "code": refactored if refactored else None
    }



# ============================================================================
# DEBUG AGENT - Debugs and explains code
# ============================================================================
def debug_agent(state: WillOfCodeState) -> WillOfCodeState:
    """Handles debugging, error analysis, and code explanation"""
    query = state["user_query"]
    file_content = state.get("file_content", "")
    code = state.get("code", file_content)
    
    prompt = f"""You are an expert Debug & Analysis Agent.
Your specialty is finding bugs, explaining code, and solving errors.

User Request: {query}

Code to Analyze:
{code if code else "No code provided."}

Instructions:
- If debugging: identify the bug, explain why it happens, and provide the fix
- If explaining: break down the code logic clearly for all skill levels
- Provide step-by-step analysis
- Include fixed code if applicable

Provide your analysis:"""
    
    result = llm_invoke(prompt)
    
    history = state.get("agent_history", []) or []
    history.append("debug")
    
    outputs = state.get("agent_outputs", {}) or {}
    outputs["debug"] = result.get("generate", "")
    
    return {
        **state,
        "current_agent": "debug",
        "agent_history": history,
        "agent_outputs": outputs,
        "llm_result": result.get("generate", "Error debugging code")
    }


# ============================================================================
# FILE AGENT - Handles file operations via MCP
# ============================================================================
def extract_path_from_query(query: str) -> str:
    """Extract file/folder path from user query"""
    import re
    # Match Windows paths like D:\folder or C:\path\to\file.py
    win_match = re.search(r'[A-Za-z]:\\[^\s"\']+', query)
    if win_match:
        return win_match.group(0)
    # Match Unix paths
    unix_match = re.search(r'/[^\s"\']+', query)
    if unix_match:
        return unix_match.group(0)
    # Match quoted paths
    quoted_match = re.search(r'["\']([^"\']+)["\']', query)
    if quoted_match:
        return quoted_match.group(1)
    return "."


def file_agent(state: WillOfCodeState) -> WillOfCodeState:
    """Handles all file operations: read, list, edit, run"""
    query = state["user_query"]
    query_lower = query.lower()
    
    logs = state.get("mcp_logs", []) or []
    result_text = ""
    
    # Extract path from query
    path = extract_path_from_query(query) or state.get("file_path", ".")
    
    # Determine file operation type
    if any(kw in query_lower for kw in ["list", "folder", "dir", "workspace", "show files"]):
        # List directory
        result = call_mcp_tool_sync("list_files", directory=path)
        if result and not result.startswith("ERROR"):
            result_text = f"**Files in {path}:**\n```\n{result}\n```"
        else:
            result_text = f"Error listing directory: {result}"
        logs.append(f"[FILE AGENT] Listed directory: {path}")
    
    elif any(kw in query_lower for kw in ["read", "open", "show file", "analyze", "get file"]):
        # Read file
        if path and path != ".":
            result = call_mcp_tool_sync("read_file", path=path)
            if result and not result.startswith("ERROR"):
                content = result
                result_text = f"**File: {path}**\n\n```\n{content}\n```"
                state["file_content"] = content
                state["file_path"] = path
            else:
                result_text = f"Error reading file: {result}"
            logs.append(f"[FILE AGENT] Read file: {path}")
        else:
            result_text = "Please specify a file path to read."
    
    elif any(kw in query_lower for kw in ["run", "execute", "python"]):
        # Run Python code - requires confirmation
        code = state.get("code", "")
        if not code:
            # Try to extract code from query
            if ":" in query:
                code = query.split(":", 1)[1].strip()
        if code:
            result_text = f"**Run Python - Confirmation Required**\n\nCode to execute:\n```python\n{code}\n```\n\nClick Accept to execute this code."
            logs.append(f"[FILE AGENT] Python execution requested")
            
            history = state.get("agent_history", []) or []
            history.append("file")
            outputs = state.get("agent_outputs", {}) or {}
            outputs["file"] = result_text
            
            return {
                **state,
                "current_agent": "file",
                "agent_history": history,
                "agent_outputs": outputs,
                "mcp_logs": logs,
                "llm_result": result_text,
                "pending_action": "run_python",
                "action_data": {"type": "run_python", "code": code}
            }
        else:
            result_text = "No code provided to execute."
    
    elif any(kw in query_lower for kw in ["delete", "remove"]):
        # Delete file - requires confirmation
        if path and path != ".":
            # For delete, we set pending_action so it requires approval
            result_text = f"**Delete Confirmation Required**\n\nAre you sure you want to delete:\n`{path}`\n\nClick Accept to confirm deletion."
            logs.append(f"[FILE AGENT] Delete requested: {path}")
            
            history = state.get("agent_history", []) or []
            history.append("file")
            outputs = state.get("agent_outputs", {}) or {}
            outputs["file"] = result_text
            
            return {
                **state,
                "current_agent": "file",
                "agent_history": history,
                "agent_outputs": outputs,
                "mcp_logs": logs,
                "llm_result": result_text,
                "pending_action": "delete",
                "action_data": {"type": "delete", "path": path}
            }
        else:
            result_text = "Please specify a file path to delete."
    
    elif any(kw in query_lower for kw in ["write", "save", "create"]):
        # Write file
        content = state.get("code", "") or state.get("file_content", "")
        if path and path != "." and content:
            result = call_mcp_tool_sync("write_file", path=path, content=content)
            if result and not result.startswith("ERROR"):
                result_text = f"**File written:** `{path}`"
            else:
                result_text = f"Error writing file: {result}"
            logs.append(f"[FILE AGENT] Wrote file: {path}")
        else:
            result_text = "Please specify a file path and content to write."
    
    else:
        result_text = "File Agent ready. Specify an operation: read, list, or run."
    
    history = state.get("agent_history", []) or []
    history.append("file")
    
    outputs = state.get("agent_outputs", {}) or {}
    outputs["file"] = result_text
    
    return {
        **state,
        "current_agent": "file",
        "agent_history": history,
        "agent_outputs": outputs,
        "mcp_logs": logs,
        "llm_result": result_text
    }


# ============================================================================
# AGENT REGISTRY - Maps agent names to their functions
# ============================================================================
AGENTS = {
    "coder": coder_agent,
    "reviewer": reviewer_agent,
    "debug": debug_agent,
    "file": file_agent,
}

def get_agent(name: str):
    """Get agent function by name"""
    return AGENTS.get(name, coder_agent)
