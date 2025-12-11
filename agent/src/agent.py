"""Main graph composition for the music store multi-agent system."""

from typing import Literal
from langgraph.graph import StateGraph, START, END

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

    # Entry point
    builder.add_edge(START, "supervisor")

    # Supervisor routes to agents or ends
    # Note: Command(goto=...) in supervisor_node handles actual runtime routing
    # These edges are for visualization only
    def supervisor_route(state: AgentState) -> Literal["customer_agent", "employee_agent", "recommendation_agent", "__end__"]:
        """Placeholder for visualization - actual routing done by Command in node."""
        return "__end__"

    builder.add_conditional_edges(
        "supervisor",
        supervisor_route,
        ["customer_agent", "employee_agent", "recommendation_agent", END]
    )

    # Agents return to supervisor
    # Note: Command(goto="supervisor") in each agent handles actual routing
    builder.add_edge("customer_agent", "supervisor")
    builder.add_edge("employee_agent", "supervisor")
    builder.add_edge("recommendation_agent", "supervisor")

    # Compile without checkpointer - LangGraph Platform handles persistence
    return builder.compile()


# Export the compiled graph
graph = create_graph()
