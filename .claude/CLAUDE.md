- use exa as the default websearch
- if you are ever unsure of something, use exa search to confirm

## LangGraph Routing Patterns

### Command vs Conditional Edges

**Command (Imperative)** - `Command(goto="node_name")`
- Routing logic inside the node with full access to state, config, and auth
- Flexible runtime decisions (e.g., LLM-based routing)
- Supports HITL with `interrupt()` and state updates
- Edges NOT visible in Studio unless `ends` parameter is used
- Docs: https://langchain-ai.github.io/langgraph/how-tos/command/

**Conditional Edges (Declarative)** - `add_conditional_edges()`
- Routing logic in separate router function
- Edges visible in Studio/graph visualization
- Static validation of node names at compile time
- Router function can access `(state, config)` including auth
- Docs: https://langchain-ai.github.io/langgraph/concepts/low_level/

### Making Command Edges Visible

Use `ends` parameter on `add_node()` to declare possible destinations:

```python
builder.add_node("supervisor", supervisor_node, ends=["agent_a", "agent_b", "__end__"])
```

This shows edges in visualization while Command handles actual runtime routing.

### Auth in Declarative Routing

Router functions can access auth via config:

```python
def router(state: AgentState, config: RunnableConfig) -> str:
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    role = auth_user.get("role")
    # routing logic
```

### When to Use Each

| Use Case | Recommended |
|----------|-------------|
| LLM decides routing | Command |
| Simple state-based routing | Conditional Edges |
| Need visualization | Command + `ends` OR Conditional Edges |
| Complex auth logic in routing | Command (cleaner) |
| Human-in-the-loop | Command + `interrupt()` |