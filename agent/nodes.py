"""
Agent Nodes - Handles AI operations with MCP tools via langchain_mcp_adapters
"""
import os
import re
import asyncio
from langgraph.types import interrupt
from agent.state import WillOfCodeState
from agent.llm import llm_invoke, llm_invoke_json
from agent.mcp_client import call_mcp_tool_sync, list_mcp_tools


def call_mcp(tool_name: str, **kwargs) -> str:
    """Sync wrapper to call MCP tool via mcp_client"""
    from agent.mcp_client import call_mcp_tool_sync
    return call_mcp_tool_sync(tool_name, **kwargs)




INTENT_KEYWORDS = {
    "run_python": ["run python", "execute python", "run code", "execute code"],
    "file_read": ["read file", "open file", "show file", "analyze file"],
    "folder_list": ["list file", "show folder", "list dir", "workspace"],
    "file_edit": ["edit file", "modify file", "change file"],
    "debug": ["debug", "fix bug", "error", "not working"],
    "explain": ["explain", "what does", "how does"],
    "code_review": ["review", "check code", "best practice"],
    "refactor": ["refactor", "improve", "clean up"],
    "test_gen": ["test", "unit test"],
    "documentation": ["document", "docstring", "comment"],
    "optimize": ["optimize", "performance", "faster"],
}


def detect_intent(query: str) -> str:
    """Detect intent using keyword matching"""
    q = query.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "generate"




def intent_node(state: WillOfCodeState) -> WillOfCodeState:
    """Detect user intent"""
    query = state.get("user_query", "")
    
    if state.get("file_content"):
        edit_words = ["add", "create", "insert", "remove", "delete", "change", "modify", "fix"]
        if any(w in query.lower() for w in edit_words):
            state["intent"] = "file_edit"
            return state
    
    state["intent"] = detect_intent(query)
    return state


def mcp_tool_node(state: WillOfCodeState) -> WillOfCodeState:
    """Unified handler for MCP-based tools (read, list, python)"""
    intent = state.get("intent")
    query = state.get("user_query", "")
    state.setdefault("mcp_logs", []).append(f"MCP: {intent}")
    
    if intent == "run_python":
        code = query.split(":", 1)[1].strip() if ":" in query else query
        result = call_mcp("run_python", code=code)
        
        if result.startswith("ERROR"):
            state["llm_result"] = f"Error: {result}"
        else:
            state["llm_result"] = f"## Python Output\n\n```\n{result}\n```"
        
    elif intent == "file_read":
        # Extract path
        path = ""
        if ":" in query:
            potential = query.split(":", 1)[1].strip()
            # Check if it looks like a Windows path (starts with drive letter) or Unix path
            if potential and (len(potential) > 2 and potential[1] == ":" or potential.startswith("/") or potential.startswith("\\")):
                path = potential
        
        if not path:
            state["llm_result"] = "Error: Please provide a file path, e.g: `read file: C:\\path\\to\\file.py`"
            return state
            
        result = call_mcp("read_file", path=path)
        if result.startswith("ERROR"):
            state["llm_result"] = f"Error: {result}"
        else:
            state["file_path"] = path
            state["file_content"] = result
            analysis = llm_invoke(f"Briefly analyze this code:\n```\n{result[:3000]}\n```").get("generate", "")
            state["llm_result"] = f"**File: {os.path.basename(path)}**\n\n{analysis}"
            
    elif intent == "folder_list":
        path = query.split(":", 1)[1].strip() if ":" in query else "."
        result = call_mcp("list_files", directory=path)
        if result.startswith("ERROR"):
            state["llm_result"] = f"Error: {result}"
        else:
            state["llm_result"] = f"**Files in {path}:**\n```\n{result}\n```"
            
    return state


def file_edit_node(state: WillOfCodeState) -> WillOfCodeState:
    """Edit file content"""
    query = state.get("user_query", "")
    content = state.get("file_content", "")
    path = state.get("file_path", "")
    
    result = llm_invoke_json(f'''You are editing a file. Make ONLY the requested change.
CRITICAL: Return the COMPLETE file content with your modification applied.
Do NOT omit any existing code - include EVERY line from the original file.

Return JSON format:
{{"modified_code": "THE COMPLETE FILE WITH ALL ORIGINAL LINES PLUS YOUR CHANGE", "changes": "brief description of what you changed"}}

User request: {query}

COMPLETE ORIGINAL FILE:
```
{content}
```

Remember: Return the ENTIRE file content, not just the changed parts.''')
    
    code = result.get("modified_code", "")
    changes = result.get("changes", "Code modified")
    
    state["pending_action"] = "stream_to_editor"
    state["action_data"] = {"type": "file_edit", "code": code, "path": path, "changes": changes}
    state["llm_result"] = f"## Changes Made\n\n{changes}\n\n*Click Save to apply*"
    return state


def generate_node(state: WillOfCodeState) -> WillOfCodeState:
    """Generate code or answer questions"""
    query = state.get("user_query", "")
    
    result = llm_invoke_json(f'''Answer this request. Return JSON:
{{"code": "code if needed", "explanation": "your answer"}}

Request: {query}''')
    
    code = result.get("code", "")
    explanation = result.get("explanation", "")
    
    state["llm_result"] = f"{explanation}\n\n```\n{code}\n```" if code else explanation
    return state


def debug_node(state: WillOfCodeState) -> WillOfCodeState:
    """Debug code"""
    code = state.get("file_content") or state.get("user_query", "")
    
    result = llm_invoke_json(f'''Debug this code. Return JSON:
{{"issues": ["issue1"], "fixed_code": "code", "explanation": "what was fixed"}}

Code: {code[:5000]}''')
    
    issues = "\n".join(f"- {i}" for i in result.get("issues", []))
    state["llm_result"] = f"**Issues:**\n{issues}\n\n**Fix:**\n{result.get('explanation', '')}\n\n```\n{result.get('fixed_code', '')}\n```"
    return state


def explain_node(state: WillOfCodeState) -> WillOfCodeState:
    """Explain code"""
    code = state.get("file_content") or state.get("user_query", "")
    result = llm_invoke(f"Explain this code clearly:\n{code[:5000]}").get("generate", "Could not explain")
    state["llm_result"] = f"**Explanation:**\n\n{result}"
    return state


def code_review_node(state: WillOfCodeState) -> WillOfCodeState:
    """Review code quality"""
    code = state.get("file_content") or state.get("user_query", "")
    
    result = llm_invoke_json(f'''Review this code. Return JSON:
{{"score": 8, "issues": ["issue"], "suggestions": ["tip"]}}

Code:
```
{code[:5000]}
```''')
    
    issues = "\n".join(f"- {i}" for i in result.get("issues", []))
    suggestions = "\n".join(f"- {i}" for i in result.get("suggestions", []))
    state["llm_result"] = f"## Code Review ({result.get('score', 7)}/10)\n\n**Issues:**\n{issues}\n\n**Suggestions:**\n{suggestions}"
    return state


def refactor_node(state: WillOfCodeState) -> WillOfCodeState:
    """Refactor code"""
    code = state.get("file_content") or state.get("user_query", "")
    
    result = llm_invoke_json(f'''Refactor this code. Return JSON:
{{"refactored_code": "code", "changes": ["change1"]}}

Code:
```
{code[:5000]}
```''')
    
    changes = "\n".join(f"- {c}" for c in result.get("changes", []))
    refactored = result.get("refactored_code", "")
    
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "refactor", "code": refactored}
    state["llm_result"] = f"## Refactored\n\n**Changes:**\n{changes}\n\n```\n{refactored}\n```"
    return state


def test_gen_node(state: WillOfCodeState) -> WillOfCodeState:
    """Generate tests"""
    code = state.get("file_content") or state.get("user_query", "")
    
    result = llm_invoke_json(f'''Generate tests. Return JSON:
{{"tests": "test code", "description": "what is tested"}}

Code:
```
{code[:5000]}
```''')
    
    state["llm_result"] = f"## Generated Tests\n\n{result.get('description', '')}\n\n```python\n{result.get('tests', '')}\n```"
    return state


def documentation_node(state: WillOfCodeState) -> WillOfCodeState:
    """Add documentation"""
    code = state.get("file_content") or state.get("user_query", "")
    
    result = llm_invoke_json(f'''Add docstrings. Return JSON:
{{"documented_code": "code with docs"}}

Code:
```
{code[:5000]}
```''')
    
    documented = result.get("documented_code", "")
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "documentation", "code": documented}
    state["llm_result"] = f"## Documented Code\n\n```\n{documented}\n```"
    return state


def optimize_node(state: WillOfCodeState) -> WillOfCodeState:
    """Optimize code"""
    code = state.get("file_content") or state.get("user_query", "")
    
    result = llm_invoke_json(f'''Optimize this code. Return JSON:
{{"optimized_code": "code", "improvements": ["improvement"]}}

Code:
```
{code[:5000]}
```''')
    
    improvements = "\n".join(f"- {i}" for i in result.get("improvements", []))
    optimized = result.get("optimized_code", "")
    
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "optimize", "code": optimized}
    state["llm_result"] = f"## Optimized\n\n**Improvements:**\n{improvements}\n\n```\n{optimized}\n```"
    return state




TOOLS = {
    "generate": generate_node,
    "debug": debug_node,
    "explain": explain_node,
    "code_review": code_review_node,
    "refactor": refactor_node,
    "test_gen": test_gen_node,
    "documentation": documentation_node,
    "optimize": optimize_node,
    "file_read": mcp_tool_node,
    "file_edit": file_edit_node,
    "folder_list": mcp_tool_node,
    "run_python": mcp_tool_node,
}


def tool_node(state: WillOfCodeState) -> WillOfCodeState:
    """Route to the right tool based on intent"""
    intent = state.get("intent", "generate")
    handler = TOOLS.get(intent, generate_node)
    return handler(state)


def should_interrupt(state: WillOfCodeState) -> str:
    """Check if we need human approval for the proposed action"""
    pending_action = state.get("pending_action")
    if pending_action == "stream_to_editor":
        return "needs_approval"
    return "no_approval"


def human_approval_node(state: WillOfCodeState) -> WillOfCodeState:
    """Pause execution and wait for human input"""
    approval_response = interrupt({
        "question": "Do you accept the proposed changes?",
        "action_data": state.get("action_data")
    })
    
    if approval_response == "accept":
        state["llm_result"] = "Changes accepted and saved."
    else:
        state["llm_result"] = "Changes rejected."
        state["pending_action"] = None
        state["action_data"] = None
        
    return state
