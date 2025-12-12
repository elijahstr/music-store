"""Supervisor node that routes to appropriate agent based on user role and intent."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from ..state import AgentState
from ..utils import get_auth_user

model = ChatAnthropic(model="claude-sonnet-4-5-20250929")

ROUTING_PROMPT = """You are a supervisor routing requests for a music store assistant system.

## USER CONTEXT
- Name: {user_name}
- Role: {role}
- {role_context}

## AGENT CAPABILITIES

### customer_agent (CUSTOMERS ONLY)
Route here when user asks about:
- Their invoices, orders, billing ("show my invoices", "what have I ordered")
- Their purchase history, music library ("what have I bought", "my purchases")
- Searching for music ("find songs by...", "search for...")
- Buying tracks or albums ("purchase", "buy")

### employee_agent (EMPLOYEES ONLY)
Route here when user asks about:
- Their employee profile ("my profile", "my info", "who is my manager")
- Customers they support ("which customers", "my customers")
- Viewing customer invoices ("show invoices for customer X")
- Editing or deleting invoices ("edit invoice", "delete invoice", "change invoice")

### recommendation_agent (ALL USERS)
Route here when user asks about:
- Music recommendations ("recommend something", "what should I listen to")
- Discovering new artists ("similar artists", "who else would I like")
- Popular tracks in genres ("top rock songs", "popular jazz tracks")

### FINISH
Output FINISH when:
- An agent has already provided a complete answer (check recent AI messages)
- The user just said hello/thanks (simple greetings)
- The request was fully handled in previous messages

## ROUTING RULES
1. Customers can ONLY use: customer_agent, recommendation_agent
2. Employees can ONLY use: employee_agent, recommendation_agent
3. Check if recent messages already contain a complete answer -> FINISH
4. When in doubt, route to the role's primary agent (customer_agent or employee_agent)

Respond with ONLY ONE of: customer_agent, employee_agent, recommendation_agent, FINISH"""


async def supervisor_node(state: AgentState, config: RunnableConfig) -> Command:
    """Route to appropriate agent based on user role and intent."""

    # Get auth context (checks multiple sources)
    auth_user = await get_auth_user(config)
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
