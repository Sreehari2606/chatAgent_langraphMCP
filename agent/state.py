"""
WillOfCode: State Definition
"""
from typing import TypedDict, List, Dict, Optional, Any


class WillOfCodeState(TypedDict):
    user_query: str
    
    intent: Optional[str]
    
    file_path: Optional[str]
    file_content: Optional[str]
    
    code: Optional[str]
    llm_result: Optional[str]
    
    pending_action: Optional[str]
    action_data: Optional[dict]
    
    mcp_logs: Optional[List[str]]