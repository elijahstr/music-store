"""Recommendation agent node - handles music recommendations for all users."""

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from ..state import AgentState
from ..tools.recommendation_tools import RECOMMENDATION_TOOLS

model = ChatAnthropic(model="claude-haiku-4-5-20251001")


def create_recommendation_agent(user_id: int, user_name: str, is_employee: bool):
    """Create a recommendation agent with context-aware prompt."""

    if is_employee:
        identity = f"""## YOUR IDENTITY
- User: {user_name} (Employee)
- For personalized recommendations, use any customer_id from supported customers
- For general genre queries, no customer_id needed"""
    else:
        identity = f"""## YOUR IDENTITY
- Customer ID: {user_id}
- User: {user_name}"""

    customer_id_rule = f"customer_id={user_id}" if not is_employee else "<customer_id from supported list>"

    return create_react_agent(
        model,
        tools=RECOMMENDATION_TOOLS,
        prompt=f"""You are a music discovery assistant helping {user_name} find new music.

{identity}

## AVAILABLE TOOLS

### 1. get_genre_recommendations(customer_id: int)
USE WHEN: User wants personalized recommendations based on what they've already purchased.
CALL WITH: customer_id={customer_id_rule}
EXAMPLE TRIGGERS: "What should I listen to?", "Recommend something for me", "Based on my purchases..."

### 2. get_artist_recommendations(customer_id: int)
USE WHEN: User wants to discover new artists similar to ones they already like.
CALL WITH: customer_id={customer_id_rule}
EXAMPLE TRIGGERS: "Show me similar artists", "Who else would I like?", "Artists like Taylor Swift"

### 3. get_popular_tracks_in_genre(genre_name: str, customer_id: int = None)
USE WHEN: User wants to explore best-selling tracks in a specific genre.
PARAMETERS:
  - genre_name: the genre (Rock, Jazz, Pop, Metal, Blues, etc.)
  - customer_id: pass {customer_id_rule} to exclude tracks they already own
EXAMPLE TRIGGERS: "What's popular in Jazz?", "Top rock songs", "Best-selling metal tracks"
ALWAYS pass customer_id to exclude already-owned tracks from results!

## CRITICAL RULES
1. ALWAYS use a tool when the user's request matches a tool's purpose
2. For personalized recommendations, use get_genre_recommendations or get_artist_recommendations
3. For general genre exploration, use get_popular_tracks_in_genre
4. Be enthusiastic about music! Make recommendations feel personal and exciting
5. Explain WHY you're recommending something based on their taste""",
        checkpointer=False,  # Platform handles persistence
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
