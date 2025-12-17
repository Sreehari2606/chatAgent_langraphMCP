import os
import re
import json
import logging
from typing import Optional, Callable, Dict
from agent.state import CodeAgentState
from agent.llm import llm_invoke, llm_invoke_json
from agent.constants import Intent, BLOCKED_PATHS, CODE_EXTENSIONS, INTENT_ROUTER, CONFIDENCE_THRESHOLDS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_llm_response(prompt: str) -> str:
    try:
        result = llm_invoke(prompt)
        if isinstance(result, dict):
            return result.get("content", result.get("generate", "No response"))
        return str(result)
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        return f"Error: {str(e)}"

def get_llm_json_response(prompt: str) -> dict:
    try:
        return llm_invoke_json(prompt)
    except Exception as e:
        logger.error(f"LLM JSON invocation failed: {e}")
        return {"response": f"Error: {str(e)}", "confidence": 0.0}

def detect_language(file_path: str) -> str:
    _, ext = os.path.splitext(file_path.lower())
    return CODE_EXTENSIONS.get(ext, "unknown")

def extract_file_path(query: str) -> Optional[str]:
    path_patterns = [
        re.compile(r'([A-Za-z]:[\\/][^\s\'"]+\.[a-zA-Z0-9]+)'),
        re.compile(r'([A-Za-z]:[\\/][^\s\'"]+)'),
        re.compile(r'(\/[^\s\'"]+\.[a-zA-Z0-9]+)'),
    ]
    for pattern in path_patterns:
        match = pattern.search(query)
        if match:
            return match.group(1)
    return None

def matches_compiled_patterns(text: str, patterns: list) -> bool:
    for pattern in patterns:
        if pattern.search(text):
            return True
    return False

def intent_decision_node(state: CodeAgentState) -> CodeAgentState:
    user_query = state.get("user_query", "")
    logger.info(f"Processing intent for query: {user_query[:50]}...")
    
    sorted_intents = sorted(INTENT_ROUTER.items(), key=lambda x: x[1]["priority"])
    for intent, config in sorted_intents:
        if config["patterns"] and matches_compiled_patterns(user_query, config["patterns"]):
            state["intent"] = intent.value
            state["confidence"] = 0.9
            logger.info(f"Matched intent: {intent.value} (confidence: 0.9)")
            return state
    
    prompt = f"""Classify this coding request. Respond in JSON format:
{{"intent": "category_name", "confidence": 0.0-1.0, "needs_clarification": true/false, "clarification_question": "question if needed"}}

Categories: generate, debug, explain, code_review, refactor, test_gen, documentation, optimize, common

Request: {user_query}"""
    
    result = get_llm_json_response(prompt)
    intent_value = result.get("intent", "generate").lower()
    confidence = result.get("confidence", 0.5)
    
    valid_intents = [i.value for i in Intent]
    state["intent"] = intent_value if intent_value in valid_intents else Intent.GENERATE.value
    state["confidence"] = confidence
    
    if result.get("needs_clarification") and confidence < CONFIDENCE_THRESHOLDS["medium"]:
        state["needs_clarification"] = True
        state["clarification_question"] = result.get("clarification_question", "Could you please provide more details?")
        state["intent"] = Intent.CLARIFY.value
    
    logger.info(f"LLM classified intent: {state['intent']} (confidence: {confidence})")
    return state

def safety_check_node(state: CodeAgentState) -> CodeAgentState:
    user_query = state.get("user_query", "").lower()
    for blocked in BLOCKED_PATHS:
        if blocked.lower() in user_query:
            state["llm_result"] = f"⚠️ Access denied: Cannot access '{blocked}' for security reasons."
            state["intent"] = Intent.COMMON.value
            state["error"] = "Security blocked"
            state["confidence"] = 1.0
            return state
    return state

def clarify_node(state: CodeAgentState) -> CodeAgentState:
    question = state.get("clarification_question", "Could you please provide more details about what you'd like me to do?")
    state["llm_result"] = f"🤔 **I need some clarification:**\n\n{question}"
    state["pending_action"] = "awaiting_clarification"
    return state

def understanding_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"Analyze this coding request and provide a clear, concise summary (2-3 sentences):\n\nRequest: {state['user_query']}\n\nSummary:"
    state["understood_problem"] = get_llm_response(prompt)
    return state

def planning_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"Create a numbered step-by-step plan to solve this problem:\n\nProblem: {state.get('understood_problem', state.get('user_query', ''))}\n\nPlan:"
    state["plan"] = get_llm_response(prompt)
    return state

def code_generation_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"""Generate clean, well-documented code for this problem. Respond in JSON:
{{"code": "your code here", "explanation": "brief explanation", "confidence": 0.0-1.0}}

Problem: {state.get('understood_problem', '')}
Plan: {state.get('plan', '')}"""
    
    result = get_llm_json_response(prompt)
    state["code"] = result.get("code", "")
    state["explanation"] = result.get("explanation", "")
    state["confidence"] = result.get("confidence", 0.7)
    return state

def explanation_node(state: CodeAgentState) -> CodeAgentState:
    code_to_explain = state.get("code") or state.get("user_query", "")
    if not code_to_explain:
        state["llm_result"] = "No code available to explain."
        return state
    
    if state.get("code"):
        confidence = state.get("confidence", 0.7)
        confidence_indicator = "🟢" if confidence >= 0.85 else "🟡" if confidence >= 0.7 else "🟠"
        state["llm_result"] = f"{confidence_indicator} **Confidence: {confidence:.0%}**\n\n**Generated Code:**\n```\n{state['code']}\n```\n\n**Explanation:**\n{state.get('explanation', '')}"
    else:
        prompt = f"""Explain this code clearly for a developer:
{code_to_explain}

Provide: 1. What the code does 2. Key components 3. Important details"""
        state["llm_result"] = f"**Explanation:**\n{get_llm_response(prompt)}"
    return state

def debug_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"""Debug this code. Respond in JSON:
{{"issues": ["issue1", "issue2"], "fixed_code": "code", "explanation": "what was fixed", "confidence": 0.0-1.0}}

Code: {state['user_query']}"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.7)
    confidence_indicator = "🟢" if confidence >= 0.85 else "🟡" if confidence >= 0.7 else "🟠"
    
    issues = result.get("issues", [])
    issues_text = "\n".join([f"- {issue}" for issue in issues]) if issues else "No specific issues identified"
    
    state["code"] = result.get("fixed_code", "")
    state["confidence"] = confidence
    state["llm_result"] = f"{confidence_indicator} **Confidence: {confidence:.0%}**\n\n**Issues Found:**\n{issues_text}\n\n**Fixed Code:**\n```\n{result.get('fixed_code', '')}\n```\n\n**Explanation:**\n{result.get('explanation', '')}"
    return state

def code_review_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Review this code. Respond in JSON:
{{"critical": ["issues"], "warnings": ["issues"], "suggestions": ["improvements"], "overall_score": 0-10, "confidence": 0.0-1.0}}

Code:
```
{code[:8000]}
```"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.8)
    score = result.get("overall_score", 7)
    
    critical = "\n".join([f"🔴 {i}" for i in result.get("critical", [])]) or "None"
    warnings = "\n".join([f"🟡 {i}" for i in result.get("warnings", [])]) or "None"
    suggestions = "\n".join([f"🟢 {i}" for i in result.get("suggestions", [])]) or "None"
    
    state["confidence"] = confidence
    state["llm_result"] = f"## 📋 Code Review (Score: {score}/10)\n\n**Critical Issues:**\n{critical}\n\n**Warnings:**\n{warnings}\n\n**Suggestions:**\n{suggestions}"
    return state

def refactor_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Refactor this code. Respond in JSON:
{{"refactored_code": "code", "changes": ["change1", "change2"], "confidence": 0.0-1.0}}

Code:
```
{code[:8000]}
```"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.75)
    changes = "\n".join([f"- {c}" for c in result.get("changes", [])])
    
    state["code"] = result.get("refactored_code", "")
    state["confidence"] = confidence
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "refactor", "code": result.get("refactored_code", "")}
    
    confidence_indicator = "🟢" if confidence >= 0.85 else "🟡" if confidence >= 0.7 else "🟠"
    state["llm_result"] = f"{confidence_indicator} **Confidence: {confidence:.0%}**\n\n## 🔄 Refactored Code\n\n**Changes Made:**\n{changes}\n\n```\n{result.get('refactored_code', '')}\n```\n\n⚠️ **Review the changes above. Click Accept to apply or Reject to cancel.**"
    return state

def test_generation_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    language = state.get("language", "python")
    prompt = f"""Generate tests for this {language} code. Respond in JSON:
{{"tests": "test code", "test_count": 5, "coverage_notes": "what's covered", "confidence": 0.0-1.0}}

Code:
```
{code[:6000]}
```"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.8)
    
    state["confidence"] = confidence
    state["llm_result"] = f"## 🧪 Generated Tests ({result.get('test_count', 'N/A')} tests)\n\n**Coverage:** {result.get('coverage_notes', 'N/A')}\n\n```{language}\n{result.get('tests', '')}\n```"
    return state

def documentation_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Add documentation to this code. Respond in JSON:
{{"documented_code": "code with docs", "docs_added": ["list of docstrings added"], "confidence": 0.0-1.0}}

Code:
```
{code[:8000]}
```"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.85)
    
    state["code"] = result.get("documented_code", "")
    state["confidence"] = confidence
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "documentation", "code": result.get("documented_code", "")}
    
    state["llm_result"] = f"## 📝 Documented Code\n\n**Added:** {len(result.get('docs_added', []))} docstrings\n\n```\n{result.get('documented_code', '')}\n```\n\n⚠️ **Review and click Accept to apply.**"
    return state

def optimize_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Optimize this code. Respond in JSON:
{{"optimized_code": "code", "improvements": ["improvement1"], "performance_gain": "estimated improvement", "confidence": 0.0-1.0}}

Code:
```
{code[:8000]}
```"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.7)
    improvements = "\n".join([f"- {i}" for i in result.get("improvements", [])])
    
    state["code"] = result.get("optimized_code", "")
    state["confidence"] = confidence
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "optimize", "code": result.get("optimized_code", "")}
    
    state["llm_result"] = f"## ⚡ Optimized Code\n\n**Performance Gain:** {result.get('performance_gain', 'N/A')}\n\n**Improvements:**\n{improvements}\n\n```\n{result.get('optimized_code', '')}\n```\n\n⚠️ **Review and click Accept to apply.**"
    return state

def common_node(state: CodeAgentState) -> CodeAgentState:
    if state.get("error"):
        return state
    prompt = f"""Respond to this query. Respond in JSON:
{{"response": "your response", "confidence": 0.0-1.0}}

Query: {state.get('user_query', '')}"""
    
    result = get_llm_json_response(prompt)
    state["confidence"] = result.get("confidence", 0.8)
    state["llm_result"] = result.get("response", "I'm not sure how to help with that.")
    return state

def folder_list_node(state: CodeAgentState) -> CodeAgentState:
    workspace = "./workspace"
    try:
        if not os.path.exists(workspace):
            os.makedirs(workspace)
        files = os.listdir(workspace)
        state["confidence"] = 1.0
        if not files:
            state["llm_result"] = "📁 Workspace is empty."
        else:
            file_list = "\n".join([f"  • {f}" for f in files])
            state["llm_result"] = f"📁 **Workspace Files:**\n{file_list}"
    except Exception as e:
        state["llm_result"] = f"Error listing files: {str(e)}"
        state["confidence"] = 0.0
    return state

def file_read_node(state: CodeAgentState) -> CodeAgentState:
    user_query = state.get("user_query", "")
    file_path = extract_file_path(user_query)
    if not file_path:
        prompt = f"Extract ONLY the file path from: {user_query}"
        file_path = get_llm_response(prompt).strip()
    if not file_path or not os.path.exists(file_path):
        state["llm_result"] = f"❌ File not found: '{file_path}'\n\nProvide a valid path like: D:\\folder\\file.py"
        state["confidence"] = 0.0
        return state
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        state["llm_result"] = f"❌ Error reading file: {str(e)}"
        state["confidence"] = 0.0
        return state
    state["file_path"] = file_path
    state["file_content"] = content
    state["language"] = detect_language(file_path)
    state["confidence"] = 1.0
    
    prompt = f"""Analyze this {state['language']} file: {os.path.basename(file_path)}

User request: {user_query}

```
{content[:8000]}
```

Provide helpful analysis."""
    analysis = get_llm_response(prompt)
    state["llm_result"] = f"📄 **{os.path.basename(file_path)}**\n\n{analysis}"
    return state

def file_edit_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"""Modify this code. Respond in JSON:
{{"modified_code": "code", "changes_summary": "what changed", "confidence": 0.0-1.0}}

Request: {state['user_query']}

Current code:
```
{state.get('file_content', '')[:8000]}
```"""
    
    result = get_llm_json_response(prompt)
    confidence = result.get("confidence", 0.7)
    
    state["updated_content"] = result.get("modified_code", "")
    state["confidence"] = confidence
    state["pending_action"] = "confirm_edit"
    state["action_data"] = {"type": "file_edit", "code": result.get("modified_code", ""), "path": state.get("file_path", "")}
    
    state["llm_result"] = f"## ✏️ Proposed Changes\n\n**Summary:** {result.get('changes_summary', 'N/A')}\n\n```\n{result.get('modified_code', '')}\n```\n\n⚠️ **Review and click Accept to apply changes.**"
    return state

def confirm_node(state: CodeAgentState) -> CodeAgentState:
    file_path = state.get('file_path', 'unknown')
    state["llm_result"] = f"📝 **Changes ready for:** {file_path}\n\nReview and confirm to apply changes."
    state["pending_action"] = "confirm_write"
    return state

def write_file_node(state: CodeAgentState) -> CodeAgentState:
    file_path = state.get("file_path", "")
    updated_content = state.get("updated_content", "")
    if not file_path or not updated_content:
        state["llm_result"] = "❌ Error: No file path or content to write."
        return state
    try:
        workspace = "./workspace"
        os.makedirs(workspace, exist_ok=True)
        full_path = os.path.join(workspace, os.path.basename(file_path))
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        state["llm_result"] = f"✅ File saved: {full_path}"
        state["pending_action"] = None
    except Exception as e:
        state["llm_result"] = f"❌ Error writing file: {str(e)}"
    return state

TOOL_HANDLERS: Dict[str, Callable] = {
    "generate": code_generation_node,
    "debug": debug_node,
    "explain": explanation_node,
    "code_review": code_review_node,
    "refactor": refactor_node,
    "test_gen": test_generation_node,
    "documentation": documentation_node,
    "optimize": optimize_node,
    "file_read": file_read_node,
    "file_edit": file_edit_node,
    "folder_list": folder_list_node,
    "common": common_node,
    "clarify": clarify_node,
}

def tool_node(state: CodeAgentState) -> CodeAgentState:
    intent = state.get("intent", "common")
    handler = TOOL_HANDLERS.get(intent, common_node)
    logger.info(f"Executing tool: {intent}")
    return handler(state)
