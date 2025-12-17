from langgraph.graph import StateGraph, START, END
from agent.state import CodeAgentState
from agent.constants import Intent, get_routing_map
from agent.nodes import (
    intent_decision_node, understanding_node, planning_node, code_generation_node,
    explanation_node, debug_node, common_node, safety_check_node, folder_list_node,
    file_read_node, file_edit_node, confirm_node, write_file_node, code_review_node,
    refactor_node, test_generation_node, documentation_node, optimize_node, clarify_node,
)

graph = StateGraph(CodeAgentState)

graph.add_node("intent", intent_decision_node)
graph.add_node("safety", safety_check_node)
graph.add_node("understand", understanding_node)
graph.add_node("plan", planning_node)
graph.add_node("generate_code", code_generation_node)
graph.add_node("explain", explanation_node)
graph.add_node("debug", debug_node)
graph.add_node("common", common_node)
graph.add_node("code_review", code_review_node)
graph.add_node("refactor", refactor_node)
graph.add_node("test_gen", test_generation_node)
graph.add_node("documentation", documentation_node)
graph.add_node("optimize", optimize_node)
graph.add_node("folder_list", folder_list_node)
graph.add_node("file_read", file_read_node)
graph.add_node("file_edit", file_edit_node)
graph.add_node("confirm", confirm_node)
graph.add_node("write_file", write_file_node)
graph.add_node("clarify", clarify_node)

def route_intent(state: CodeAgentState) -> str:
    return state.get("intent", Intent.GENERATE.value)

graph.add_edge(START, "intent")
graph.add_edge("intent", "safety")

graph.add_conditional_edges("safety", route_intent, get_routing_map())

graph.add_edge("understand", "plan")
graph.add_edge("plan", "generate_code")
graph.add_edge("generate_code", "explain")
graph.add_edge("explain", END)
graph.add_edge("file_edit", "confirm")
graph.add_edge("confirm", "write_file")
graph.add_edge("write_file", END)
graph.add_edge("file_read", END)
graph.add_edge("folder_list", END)
graph.add_edge("debug", END)
graph.add_edge("common", END)
graph.add_edge("code_review", END)
graph.add_edge("refactor", END)
graph.add_edge("test_gen", END)
graph.add_edge("documentation", END)
graph.add_edge("optimize", END)
graph.add_edge("clarify", END)

code_agent = graph.compile()
