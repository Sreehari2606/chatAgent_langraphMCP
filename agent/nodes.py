import os
import re
import logging
from typing import Optional
from agent.state import CodeAgentState
from agent.llm import llm_invoke
from agent.constants import Intent, BLOCKED_PATHS, CODE_EXTENSIONS, INTENT_ROUTER

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

def detect_language(file_path: str) -> str:
    _, ext = os.path.splitext(file_path.lower())
    return CODE_EXTENSIONS.get(ext, "unknown")

def extract_file_path(query: str) -> Optional[str]:
    path_patterns = [
        r'([A-Za-z]:[\\/][^\s\'"]+\.[a-zA-Z0-9]+)',
        r'([A-Za-z]:[\\/][^\s\'"]+)',
        r'(\/[^\s\'"]+\.[a-zA-Z0-9]+)',
    ]
    for pattern in path_patterns:
        match = re.search(pattern, query)
        if match:
            return match.group(1)
    return None

def matches_patterns(text: str, patterns: list) -> bool:
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False

def intent_decision_node(state: CodeAgentState) -> CodeAgentState:
    user_query = state.get("user_query", "")
    logger.info(f"Processing intent for query: {user_query[:50]}...")
    
    sorted_intents = sorted(INTENT_ROUTER.items(), key=lambda x: x[1]["priority"])
    for intent, config in sorted_intents:
        if config["patterns"] and matches_patterns(user_query, config["patterns"]):
            state["intent"] = intent.value
            logger.info(f"Matched intent: {intent.value}")
            return state
    
    prompt = f"""Classify this coding request into ONE category:
- generate: create new code
- debug: fix bugs or errors
- explain: explain code or concepts
- code_review: review code quality
- refactor: improve code structure
- test_gen: generate tests
- documentation: add docs/comments
- optimize: improve performance
- common: non-coding question

Reply with ONLY the category name.

Request: {user_query}"""
    response = get_llm_response(prompt).strip().lower()
    valid_intents = [i.value for i in Intent]
    state["intent"] = response if response in valid_intents else Intent.GENERATE.value
    logger.info(f"LLM classified intent: {state['intent']}")
    return state

def safety_check_node(state: CodeAgentState) -> CodeAgentState:
    user_query = state.get("user_query", "").lower()
    for blocked in BLOCKED_PATHS:
        if blocked.lower() in user_query:
            state["llm_result"] = f"⚠️ Access denied: Cannot access '{blocked}' for security reasons."
            state["intent"] = Intent.COMMON.value
            state["error"] = "Security blocked"
            return state
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
    prompt = f"""Generate clean, well-documented code for this problem:

Problem: {state.get('understood_problem', '')}

Plan: {state.get('plan', '')}

Requirements:
- Include clear comments
- Follow best practices
- Handle edge cases

Code:"""
    state["code"] = get_llm_response(prompt)
    return state

def explanation_node(state: CodeAgentState) -> CodeAgentState:
    code_to_explain = state.get("code") or state.get("user_query", "")
    if not code_to_explain:
        state["llm_result"] = "No code available to explain."
        return state
    prompt = f"""Explain this code clearly for a developer:

{code_to_explain}

Provide:
1. What the code does (overview)
2. Key components and their purpose
3. Important implementation details"""
    explanation = get_llm_response(prompt)
    state["explanation"] = explanation
    if state.get("code"):
        state["llm_result"] = f"**Generated Code:**\n```\n{state['code']}\n```\n\n**Explanation:**\n{explanation}"
    else:
        state["llm_result"] = f"**Explanation:**\n{explanation}"
    return state

def debug_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"""Debug this code and provide fixed version:

{state['user_query']}

Provide:
1. Identified issues
2. Fixed code
3. Explanation of fixes"""
    fixed_code = get_llm_response(prompt)
    state["code"] = fixed_code
    state["llm_result"] = fixed_code
    return state

def code_review_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Perform a comprehensive code review:

```
{code[:8000]}
```

Review for:
1. **Code Quality**: Readability, naming, structure
2. **Best Practices**: Design patterns, DRY, SOLID
3. **Potential Bugs**: Edge cases, error handling
4. **Security**: Input validation, vulnerabilities
5. **Performance**: Inefficiencies, optimizations

Format as a structured review with severity levels (🔴 Critical, 🟡 Warning, 🟢 Suggestion)."""
    review = get_llm_response(prompt)
    state["llm_result"] = f"## 📋 Code Review\n\n{review}"
    return state

def refactor_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Refactor this code for better quality:

```
{code[:8000]}
```

Apply:
1. Extract functions for repeated code
2. Improve naming conventions
3. Add proper error handling
4. Simplify complex logic
5. Follow SOLID principles

Provide the refactored code with explanations of changes."""
    refactored = get_llm_response(prompt)
    state["code"] = refactored
    state["llm_result"] = f"## 🔄 Refactored Code\n\n{refactored}"
    return state

def test_generation_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    language = state.get("language", "python")
    prompt = f"""Generate comprehensive unit tests for this {language} code:

```
{code[:6000]}
```

Include:
1. Test for normal cases
2. Test for edge cases
3. Test for error handling
4. Mock external dependencies if needed

Use pytest for Python, Jest for JavaScript, or appropriate testing framework."""
    tests = get_llm_response(prompt)
    state["llm_result"] = f"## 🧪 Generated Tests\n\n{tests}"
    return state

def documentation_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Add comprehensive documentation to this code:

```
{code[:8000]}
```

Add:
1. Module/file docstring with description
2. Function/method docstrings with Args, Returns, Raises
3. Class docstrings with Attributes
4. Inline comments for complex logic
5. Type hints where appropriate

Return the fully documented code."""
    documented = get_llm_response(prompt)
    state["code"] = documented
    state["llm_result"] = f"## 📝 Documented Code\n\n{documented}"
    return state

def optimize_node(state: CodeAgentState) -> CodeAgentState:
    code = state.get("file_content") or state.get("user_query", "")
    prompt = f"""Optimize this code for better performance:

```
{code[:8000]}
```

Focus on:
1. Algorithm efficiency (time complexity)
2. Memory usage (space complexity)
3. Reducing unnecessary operations
4. Caching/memoization where beneficial
5. Using efficient data structures

Provide optimized code with performance analysis."""
    optimized = get_llm_response(prompt)
    state["code"] = optimized
    state["llm_result"] = f"## ⚡ Optimized Code\n\n{optimized}"
    return state

def common_node(state: CodeAgentState) -> CodeAgentState:
    if state.get("error"):
        return state
    prompt = f"""The user asked: {state.get('user_query', '')}

This appears to be a general question. Provide a helpful, concise response.
If it's completely unrelated to programming, politely explain that you're a coding assistant."""
    response = get_llm_response(prompt)
    state["llm_result"] = response
    return state

def folder_list_node(state: CodeAgentState) -> CodeAgentState:
    workspace = "./workspace"
    try:
        if not os.path.exists(workspace):
            os.makedirs(workspace)
        files = os.listdir(workspace)
        if not files:
            state["llm_result"] = "📁 Workspace is empty."
        else:
            file_list = "\n".join([f"  • {f}" for f in files])
            state["llm_result"] = f"📁 **Workspace Files:**\n{file_list}"
    except Exception as e:
        state["llm_result"] = f"Error listing files: {str(e)}"
    return state

def file_read_node(state: CodeAgentState) -> CodeAgentState:
    user_query = state.get("user_query", "")
    file_path = extract_file_path(user_query)
    if not file_path:
        prompt = f"Extract ONLY the file path from: {user_query}"
        file_path = get_llm_response(prompt).strip()
    if not file_path or not os.path.exists(file_path):
        state["llm_result"] = f"❌ File not found: '{file_path}'\n\nProvide a valid path like: D:\\folder\\file.py"
        return state
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        state["llm_result"] = f"❌ Error reading file: {str(e)}"
        return state
    state["file_path"] = file_path
    state["file_content"] = content
    state["language"] = detect_language(file_path)
    prompt = f"""Analyze this {state['language']} file: {os.path.basename(file_path)}

User request: {user_query}

```
{content[:8000]}
```

Provide helpful analysis based on what the user wants."""
    analysis = get_llm_response(prompt)
    state["llm_result"] = f"📄 **{os.path.basename(file_path)}**\n\n{analysis}"
    return state

def file_edit_node(state: CodeAgentState) -> CodeAgentState:
    prompt = f"""Modify this code based on the request:

Request: {state['user_query']}

Current code:
```
{state.get('file_content', '')[:8000]}
```

Return ONLY the modified code."""
    updated = get_llm_response(prompt)
    state["updated_content"] = updated
    return state

def confirm_node(state: CodeAgentState) -> CodeAgentState:
    file_path = state.get('file_path', 'unknown')
    state["llm_result"] = f"📝 **Changes ready for:** {file_path}\n\nReview and confirm to apply changes."
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
    except Exception as e:
        state["llm_result"] = f"❌ Error writing file: {str(e)}"
    return state
