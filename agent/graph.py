"""
WillOfCode: Multi-Agent State Graph with Supervisor Pattern
Uses LangGraph with 4 specialized agents orchestrated by a supervisor
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import WillOfCodeState
from agent.supervisor import (
    supervisor_node, 
    should_need_approval, 
    human_approval_node
)
from agent.agents import coder_agent, reviewer_agent, debug_agent, file_agent


# Create the multi-agent graph
graph = StateGraph(WillOfCodeState)


# Add nodes
graph.add_node("supervisor", supervisor_node)           # Routes to the right agent
graph.add_node("coder", coder_agent)                    # Code generation agent
graph.add_node("reviewer", reviewer_agent)              # Code review agent
graph.add_node("debug", debug_agent)                    # Debug & explain agent
graph.add_node("file", file_agent)                      # File operations agent
graph.add_node("human_approval", human_approval_node)   # Human-in-the-loop


# Define the routing logic from supervisor to agents
def route_to_agent(state: WillOfCodeState) -> str:
    """Route to the selected agent based on supervisor decision"""
    return state.get("current_agent", "coder")


# Connect the graph
graph.add_edge(START, "supervisor")

# Supervisor routes to the appropriate agent
graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "coder": "coder",
        "reviewer": "reviewer",
        "debug": "debug",
        "file": "file",
    }
)

# All agents can optionally go to human approval or end
graph.add_conditional_edges("coder", should_need_approval, {"needs_approval": "human_approval", "no_approval": END})
graph.add_conditional_edges("reviewer", should_need_approval, {"needs_approval": "human_approval", "no_approval": END})
graph.add_conditional_edges("debug", should_need_approval, {"needs_approval": "human_approval", "no_approval": END})
graph.add_conditional_edges("file", should_need_approval, {"needs_approval": "human_approval", "no_approval": END})

graph.add_edge("human_approval", END)


# Compile with memory checkpointer
checkpointer = MemorySaver()
will_of_code = graph.compile(checkpointer=checkpointer)


# Export agent info for API
AVAILABLE_AGENTS = {
    "coder": "Generates new code, creates files, writes functions",
    "reviewer": "Reviews code quality, refactors, suggests improvements",
    "debug": "Debugs errors, explains code, traces issues",
    "file": "Reads files, lists directories, executes Python",
}
