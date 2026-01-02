"""
WillOfCode: Supervisor Agent
Routes user requests using keyword-based intent detection (MCP style)
"""
from agent.state import WillOfCodeState
from agent.agents import AGENTS, get_agent


# Keyword-based intent detection for efficient routing
INTENT_KEYWORDS = {
    "run_python": ["run python", "execute python", "run code", "execute code"],
    "file_read": ["read file", "open file", "show file", "analyze file"],
    "folder_list": ["list file", "show folder", "list dir", "workspace"],
    "file_edit": ["edit file", "modify file", "change file"],
    "file_write": ["write file", "save file", "create file"],
    "file_delete": ["delete file", "remove file", "delete"],
    "debug": ["debug", "fix bug", "error", "not working"],
    "explain": ["explain", "what does", "how does"],
    "code_review": ["review", "check code", "best practice"],
    "refactor": ["refactor", "improve", "clean up"],
    "test_gen": ["test", "unit test"],
    "documentation": ["document", "docstring", "comment"],
    "optimize": ["optimize", "performance", "faster"],
}
 
# Map intents to agents
INTENT_TO_AGENT = {
    # File Agent handles
    "run_python": "file",
    "file_read": "file",
    "folder_list": "file",
    "file_edit": "file",
    "file_write": "file",
    "file_delete": "file",
    
    # Debug Agent handles
    "debug": "debug",
    "explain": "debug",
    
    # Reviewer Agent handles
    "code_review": "reviewer",
    "refactor": "reviewer",
    "optimize": "reviewer",
    
    # Coder Agent handles
    "test_gen": "coder",
    "documentation": "coder",
}


def detect_intent(query: str) -> str:
    """Detect intent using keyword matching (MCP style)"""
    q = query.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "generate"  # Default intent


def get_agent_for_intent(intent: str) -> str:
    """Map intent to the appropriate agent"""
    return INTENT_TO_AGENT.get(intent, "coder")


def supervisor_node(state: WillOfCodeState) -> WillOfCodeState:
    """
    Supervisor Agent: Routes to the best agent using keyword matching
    Fast and efficient - no LLM call needed for routing
    """
    query = state["user_query"]
    
    # Detect intent using keywords
    intent = detect_intent(query)
    
    # Map intent to agent
    selected_agent = get_agent_for_intent(intent)
    
    return {
        **state,
        "current_agent": selected_agent,
        "intent": intent,
    }


def should_need_approval(state: WillOfCodeState) -> str:
    """
    Determines if human approval is needed based on the action
    """
    pending = state.get("pending_action")
    # Trigger approval for code edits (shown in diff modal)
    if pending in ["stream_to_editor", "file_edit", "run_python", "delete"]:
        return "needs_approval"
    return "no_approval"


def human_approval_node(state: WillOfCodeState) -> WillOfCodeState:
    """
    Human-in-the-loop approval node
    """
    from langgraph.types import interrupt
    
    action = state.get("pending_action", "unknown")
    data = state.get("action_data", {})
    
    # Create approval request
    approval_request = {
        "action": action,
        "data": data,
        "message": f"Approval needed for: {action}"
    }
    
    # Interrupt for human input
    human_response = interrupt(approval_request)
    
    if human_response.get("approved", False):
        return {
            **state,
            "llm_result": state.get("llm_result", "") + "\n[Action approved and executed]"
        }
    else:
        return {
            **state,
            "llm_result": "[Action rejected by user]"
        }
