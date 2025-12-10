"""Main graph composition for the music store multi-agent system."""

from langgraph.graph import StateGraph, START

from .state import AgentState
from .nodes import (
    supervisor_node,
    customer_agent_node,
    employee_agent_node,
    recommendation_agent_node,
)


def create_graph():
    """Create and compile the multi-agent graph."""

    builder = StateGraph(AgentState)

    # Add all nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("customer_agent", customer_agent_node)
    builder.add_node("employee_agent", employee_agent_node)
    builder.add_node("recommendation_agent", recommendation_agent_node)

    # Entry point - always start with supervisor
    builder.add_edge(START, "supervisor")

    # Supervisor can route to any agent or end
    # (routing is handled by Command in supervisor_node)

    # All agents route back to supervisor after completing
    # (routing is handled by Command in each agent node)

    # Compile without checkpointer - LangGraph Platform handles persistence
    return builder.compile()


# Export the compiled graph
graph = create_graph()
