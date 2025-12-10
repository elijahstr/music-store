"""Employee agent node - handles employee queries with HITL for invoice mutations."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from ..state import AgentState
from ..tools.employee_tools import EMPLOYEE_TOOLS, HITL_TOOLS

model = ChatAnthropic(model="claude-haiku-4-5-20251015")


def create_employee_agent(employee_id: int, employee_name: str, supported_customers: list[int]):
    """Create an employee agent with context-aware prompt."""
    return create_react_agent(
        model,
        tools=EMPLOYEE_TOOLS,
        prompt=f"""You are a helpful assistant for {employee_name}, an employee at our music store.

Employee ID: {employee_id}
Supported Customer IDs: {supported_customers}

IMPORTANT RULES:
- For your own info: use employee_id={employee_id}
- For customer queries: ONLY use customer_id values from {supported_customers}
- edit_invoice and delete_invoice require MANAGER APPROVAL

You can help with:
- Viewing your employee profile (get_employee_info)
- Seeing your supported customers (get_supported_customers)
- Viewing customer invoices (get_customer_invoices)
- Editing invoices (edit_invoice) - requires approval
- Deleting invoices (delete_invoice) - requires approval

Be professional and thorough. Always verify you support a customer before accessing their data."""
    )


async def employee_agent_node(state: AgentState, config: RunnableConfig) -> Command:
    """Employee agent node with human-in-the-loop for invoice mutations."""

    # Get auth context
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    employee_id = auth_user.get("employee_id")
    employee_name = auth_user.get("name", "Employee")
    supported_customers = auth_user.get("supported_customers", [])

    # Create agent with employee context
    agent = create_employee_agent(employee_id, employee_name, supported_customers)

    # Invoke agent
    result = await agent.ainvoke(
        {"messages": state["messages"]},
        config=config
    )

    # Check if any tool calls require HITL approval
    last_msg = result["messages"][-1] if result["messages"] else None

    if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        for tool_call in last_msg.tool_calls:
            if tool_call["name"] in HITL_TOOLS:
                # Trigger human-in-the-loop interrupt
                approval_request = {
                    "type": "manager_approval",
                    "action": tool_call["name"],
                    "args": tool_call["args"],
                    "message": f"Manager Approval Required\n\nAction: {tool_call['name']}\nInvoice ID: {tool_call['args'].get('invoice_id')}\n\nDo you approve this action?"
                }

                # This will pause execution and wait for human input
                approval = interrupt(approval_request)

                if not approval or not approval.get("approved", False):
                    # Action was rejected
                    return Command(
                        goto="supervisor",
                        update={
                            "messages": [
                                AIMessage(content="The action was not approved by the manager. No changes were made.")
                            ]
                        }
                    )

                # Action was approved - the tool already executed in the agent
                # Add confirmation message
                return Command(
                    goto="supervisor",
                    update={
                        "messages": result["messages"] + [
                            AIMessage(content="Manager approval received. Action completed successfully.")
                        ]
                    }
                )

    return Command(
        goto="supervisor",
        update={"messages": result["messages"]}
    )
