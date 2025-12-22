"""
WillOfCode: State Graph with Human-in-the-Loop Support
Uses LangGraph's interrupt() for proper human approval flow
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import WillOfCodeState
from agent.nodes import intent_node, tool_node, human_approval_node, should_interrupt

# Create the graph
graph = StateGraph(WillOfCodeState)


graph.add_node("intent", intent_node)          # Detect what user wants
graph.add_node("tool", tool_node)              # Execute the right tool
graph.add_node("human_approval", human_approval_node)  # Human-in-the-loop


graph.add_edge(START, "intent")
graph.add_edge("intent", "tool")


graph.add_conditional_edges(
    "tool",
    should_interrupt,
    {
        "needs_approval": "human_approval",
        "no_approval": END
    }
)
graph.add_edge("human_approval", END)


checkpointer = MemorySaver()
will_of_code = graph.compile(checkpointer=checkpointer)
