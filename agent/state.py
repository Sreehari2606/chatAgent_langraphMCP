"""
WillOfCode: Multi-Agent State Definition
Supports Supervisor Pattern with specialized agents
"""
from typing import TypedDict, List, Dict, Optional, Any


class WillOfCodeState(TypedDict):
    user_query: str
    
    # Multi-agent fields
    current_agent: Optional[str]          # Which agent is currently active
    agent_history: Optional[List[str]]    # Track which agents have been used
    agent_outputs: Optional[Dict[str, str]]  # Outputs from each agent
    
    intent: Optional[str]
    
    file_path: Optional[str]
    file_content: Optional[str]
    
    code: Optional[str]
    llm_result: Optional[str]
    
    pending_action: Optional[str]
    action_data: Optional[dict]
    
    mcp_logs: Optional[List[str]]