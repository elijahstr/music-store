"""Employee agent node - handles employee queries with HITL for invoice mutations."""

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from ..state import AgentState
from ..tools.employee_tools import EMPLOYEE_TOOLS

model = ChatAnthropic(model="claude-sonnet-4-5-20250929")


def create_employee_agent(employee_id: int, employee_name: str, supported_customers: list[int]):
    """Create an employee agent with context-aware prompt."""
    return create_react_agent(
        model,
        tools=EMPLOYEE_TOOLS,
        prompt=f"""You are a helpful assistant for {employee_name}, an employee at our music store.

## YOUR IDENTITY
- Employee ID: {employee_id}
- Supported Customer IDs: {supported_customers}

## AVAILABLE TOOLS

### 1. get_employee_info(employee_id: int)
USE WHEN: User asks about their own profile, title, hire date, contact info, or who they report to.
ALWAYS CALL WITH: employee_id={employee_id}
EXAMPLE TRIGGERS: "Show my profile", "Who is my manager?", "What's my title?"

### 2. get_supported_customers(employee_id: int)
USE WHEN: User asks who they support, their customer list, or wants to see all their assigned customers.
ALWAYS CALL WITH: employee_id={employee_id}
EXAMPLE TRIGGERS: "Which customers do I support?", "Show my customers", "Who do I work with?"

### 3. get_customer_invoices(customer_id: int)
USE WHEN: User wants to see invoices for a specific customer they support.
PARAMETER: customer_id must be one of {supported_customers}
EXAMPLE TRIGGERS: "Show invoices for customer 60", "What are Jake's invoices?"

### 4. edit_invoice(invoice_id: int, new_total: float)
USE WHEN: User wants to change/update/modify an invoice amount.
REQUIRES: Manager approval (automatic interrupt)
EXAMPLE TRIGGERS: "Change invoice 413 to $50", "Update the total on invoice 415"

### 5. delete_invoice(invoice_id: int)
USE WHEN: User explicitly wants to DELETE/REMOVE an invoice.
REQUIRES: Manager approval (automatic interrupt)
EXAMPLE TRIGGERS: "Delete invoice 413", "Remove invoice 415"

## CRITICAL RULES
1. ALWAYS use a tool when the user's request matches a tool's purpose
2. For your own info, ALWAYS use employee_id={employee_id}
3. For customer data, ONLY use customer_id values from {supported_customers}
4. edit_invoice and delete_invoice will automatically pause for manager approval
5. If unsure which customer, call get_supported_customers first to show options

Be professional and thorough.""",
        checkpointer=False,  # Platform handles persistence
    )


async def employee_agent_node(state: AgentState, config: RunnableConfig) -> Command:
    """Employee agent node with human-in-the-loop for invoice mutations.

    HITL is handled inside the tools themselves via interrupt().
    """

    # Get auth context
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    employee_id = auth_user.get("employee_id")
    employee_name = auth_user.get("name", "Employee")
    supported_customers = auth_user.get("supported_customers", [])

    # Create agent with employee context
    agent = create_employee_agent(employee_id, employee_name, supported_customers)

    # Invoke agent - HITL interrupts happen inside tools when needed
    result = await agent.ainvoke(
        {"messages": state["messages"]},
        config=config
    )

    return Command(
        goto="supervisor",
        update={"messages": result["messages"]}
    )
