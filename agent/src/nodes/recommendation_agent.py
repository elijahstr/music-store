"""Recommendation agent node - handles music recommendations for all users."""

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from ..state import AgentState
from ..tools.recommendation_tools import RECOMMENDATION_TOOLS

model = ChatAnthropic(model="claude-haiku-4-5-20251015")


def create_recommendation_agent(user_id: int, user_name: str, is_employee: bool):
    """Create a recommendation agent with context-aware prompt."""

    if is_employee:
        context = f"""You are helping {user_name}, an employee, explore music recommendations.

For personal recommendations, you can use any customer_id they support.
For general queries about genres and popular tracks, no customer_id is needed."""
    else:
        context = f"""You are helping {user_name} discover new music based on their taste.

Customer ID: {user_id}
IMPORTANT: When using tools that need customer_id, always use customer_id={user_id}"""

    return create_react_agent(
        model,
        tools=RECOMMENDATION_TOOLS,
        prompt=f"""{context}

You can help with:
- Personalized recommendations based on purchase history (get_genre_recommendations)
- Finding similar artists (get_artist_recommendations)
- Exploring popular tracks in a genre (get_popular_tracks_in_genre)

Be enthusiastic about music! Make recommendations feel personal and exciting."""
    )


async def recommendation_agent_node(state: AgentState, config: RunnableConfig) -> Command:
    """Recommendation agent node function."""

    # Get auth context
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    role = auth_user.get("role", "customer")
    user_name = auth_user.get("name", "User")

    if role == "employee":
        user_id = auth_user.get("employee_id")
        is_employee = True
    else:
        user_id = auth_user.get("customer_id")
        is_employee = False

    # Create agent with user context
    agent = create_recommendation_agent(user_id, user_name, is_employee)

    # Invoke agent
    result = await agent.ainvoke(
        {"messages": state["messages"]},
        config=config
    )

    return Command(
        goto="supervisor",
        update={"messages": result["messages"]}
    )
