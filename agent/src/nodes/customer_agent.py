"""Customer agent node - handles customer queries about their own account."""

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from ..state import AgentState
from ..tools.customer_tools import CUSTOMER_TOOLS

model = ChatAnthropic(model="claude-haiku-4-5-20251015")


def create_customer_agent(customer_id: int, customer_name: str):
    """Create a customer agent with context-aware prompt."""
    return create_react_agent(
        model,
        tools=CUSTOMER_TOOLS,
        prompt=f"""You are a helpful assistant for {customer_name}, a customer at our music store.

Customer ID: {customer_id}

IMPORTANT: When using ANY tool, you MUST pass customer_id={customer_id}

You can help with:
- Viewing invoices (use get_my_invoices)
- Seeing purchase history (use get_my_purchases)
- Getting invoice details (use get_invoice_details)

Be friendly and helpful. Format responses nicely with the information retrieved."""
    )


async def customer_agent_node(state: AgentState, config: RunnableConfig) -> Command:
    """Customer agent node function."""

    # Get auth context
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    customer_id = auth_user.get("customer_id")
    customer_name = auth_user.get("name", "Customer")

    # Create agent with customer context
    agent = create_customer_agent(customer_id, customer_name)

    # Invoke agent
    result = await agent.ainvoke(
        {"messages": state["messages"]},
        config=config
    )

    return Command(
        goto="supervisor",
        update={"messages": result["messages"]}
    )
