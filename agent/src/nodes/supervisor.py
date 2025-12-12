"""Supervisor node that routes to appropriate agent based on user role and intent."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from ..state import AgentState
from ..utils import get_auth_user

model = ChatAnthropic(model="claude-haiku-4-5-20251001")

# Maximum supervisor invocations before forcing exit (prevents infinite loops)
MAX_SUPERVISOR_TURNS = 2

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

### FINISH (PREFER THIS)
Output FINISH when:
- An agent has already provided ANY substantive response (check recent AI messages)
- The user just said hello/thanks/goodbye (simple greetings)
- The request was handled in previous messages
- An agent returned data or answered the question - DO NOT re-route unnecessarily

## ROUTING RULES
1. Customers can ONLY use: customer_agent, recommendation_agent
2. Employees can ONLY use: employee_agent, recommendation_agent
3. **IMPORTANT**: If an agent just responded with data or an answer, output FINISH immediately
4. Only route to another agent if the user's request was NOT addressed
5. Prefer FINISH over unnecessary agent calls - minimize latency

Respond with ONLY ONE of: customer_agent, employee_agent, recommendation_agent, FINISH"""


async def supervisor_node(state: AgentState, config: RunnableConfig) -> Command:
    """Route to appropriate agent based on user role and intent."""

    # Track supervisor invocations to prevent infinite loops
    # Reset counter if last message is from human (new user request)
    last_msg = state["messages"][-1] if state["messages"] else None
    is_new_request = (
        last_msg and
        (getattr(last_msg, "type", None) == "human" or
         (isinstance(last_msg, dict) and last_msg.get("role") == "human"))
    )

    current_turns = 0 if is_new_request else state.get("supervisor_turns", 0)

    # Force exit if we've hit max turns for this request
    if current_turns >= MAX_SUPERVISOR_TURNS:
        return Command(goto="__end__", update={"supervisor_turns": 0})

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

    # Increment turn counter for next invocation
    new_turns = current_turns + 1

    if next_agent == "finish":
        return Command(goto="__end__", update={"supervisor_turns": new_turns})

    return Command(goto=next_agent, update={"supervisor_turns": new_turns})
