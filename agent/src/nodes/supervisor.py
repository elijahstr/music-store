"""Supervisor node that routes to appropriate agent based on user role and intent."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from ..state import AgentState

model = ChatAnthropic(model="claude-opus-4-5-20250929")

ROUTING_PROMPT = """You are a supervisor routing requests for a music store assistant system.

User Information:
- Name: {user_name}
- Role: {role}
- {role_context}

Review the conversation and decide what to do next:

AGENTS:
- "customer_agent": For viewing personal invoices, purchase history, account information
- "employee_agent": For employee info, viewing/managing supported customers, editing invoices
- "recommendation_agent": For music recommendations, discovering new artists, genre exploration
- "FINISH": When the user's request has been fully answered

RULES:
- Customers can ONLY use: customer_agent, recommendation_agent
- Employees can ONLY use: employee_agent, recommendation_agent
- If an agent has already provided a complete answer, output FINISH
- For greetings or simple questions, output FINISH

Respond with ONLY the agent name (customer_agent, employee_agent, recommendation_agent, or FINISH)."""


async def supervisor_node(state: AgentState, config: RunnableConfig) -> Command:
    """Route to appropriate agent based on user role and intent."""

    # Get auth context
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    role = auth_user.get("role", "customer")
    user_name = auth_user.get("name", "User")

    # Build role-specific context
    if role == "employee":
        supported = auth_user.get("supported_customers", [])
        role_context = f"Supported Customer IDs: {supported}"
        valid_agents = ["employee_agent", "recommendation_agent", "FINISH"]
    else:
        role_context = f"Customer ID: {auth_user.get('customer_id', 'unknown')}"
        valid_agents = ["customer_agent", "recommendation_agent", "FINISH"]

    # Build conversation summary for routing decision
    # Include last few messages to understand context
    recent_messages = []
    for msg in state["messages"][-6:]:  # Last 6 messages for context
        if hasattr(msg, "type"):
            msg_type = msg.type
            content = msg.content if hasattr(msg, "content") else str(msg)
        elif isinstance(msg, dict):
            msg_type = msg.get("role", "unknown")
            content = msg.get("content", "")
        else:
            continue
        # Truncate long messages
        if len(content) > 500:
            content = content[:500] + "..."
        recent_messages.append(f"{msg_type}: {content}")

    conversation_context = "\n".join(recent_messages)

    # Ask LLM to route
    response = await model.ainvoke([
        SystemMessage(content=ROUTING_PROMPT.format(
            user_name=user_name,
            role=role,
            role_context=role_context
        )),
        HumanMessage(content=f"Recent conversation:\n{conversation_context}\n\nWhat should we do next?")
    ])

    next_agent = response.content.strip().lower()

    # Validate and enforce role restrictions
    if next_agent not in [a.lower() for a in valid_agents]:
        # Default to the primary agent for the role
        next_agent = "customer_agent" if role == "customer" else "employee_agent"

    if next_agent == "finish":
        return Command(goto="__end__")

    return Command(goto=next_agent)
