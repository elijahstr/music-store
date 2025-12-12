"""Shared state definition for the multi-agent system."""

from typing import Literal, Optional
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Extended state for multi-agent music store system."""

    # User context (set from auth)
    user_role: Literal["employee", "customer"]
    user_id: int  # employee_id or customer_id depending on role
    user_name: str
    supported_customers: list[int]  # For employees only, empty for customers

    # Routing
    next_agent: Optional[str]

    # Turn tracking for latency control
    supervisor_turns: int  # Counts supervisor invocations, forces exit after MAX_TURNS
