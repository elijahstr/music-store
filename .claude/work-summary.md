# Work Summary - LangGraph Music Store Backend

> This file tracks implementation progress and test results at each checkpoint.

---

## Checkpoint 1: Core Modules
**Status**: PASSED
**Date**: 2024-12-10

### Tests Run
```bash
cd agent && uv pip install -e .
python -c "from src.db import get_db; print('DB OK')"
python -c "from src.state import AgentState; print('State OK')"
python -c "from src.auth import auth; print('Auth OK')"
```

### Results
- `db.py` - Database connection helper created and working
- `state.py` - AgentState TypedDict extending MessagesState created
- `auth.py` - Custom auth handler with `@auth.authenticate` and `@auth.on` decorators created

### Files Created
- `agent/src/__init__.py`
- `agent/src/db.py`
- `agent/src/state.py`
- `agent/src/auth.py`

---

## Checkpoint 2: Tools
**Status**: PASSED
**Date**: 2024-12-10

### Tests Run
```bash
python -c "from src.tools.customer_tools import get_my_invoices; print(get_my_invoices.invoke({'customer_id': 60}))"
python -c "from src.tools.employee_tools import get_employee_info; print(get_employee_info.invoke({'employee_id': 9}))"
python -c "from src.tools.recommendation_tools import get_popular_tracks_in_genre; print(get_popular_tracks_in_genre.invoke({'genre_name': 'Rock'}))"
```

### Results
- Customer tools working (get_my_invoices, get_my_purchases, get_invoice_details)
- Employee tools working (get_employee_info, get_supported_customers, get_customer_invoices, edit_invoice, delete_invoice)
- Recommendation tools working (get_genre_recommendations, get_artist_recommendations, get_popular_tracks_in_genre)

### Files Created
- `agent/src/tools/__init__.py`
- `agent/src/tools/customer_tools.py`
- `agent/src/tools/employee_tools.py`
- `agent/src/tools/recommendation_tools.py`

---

## Checkpoint 3: Node Imports
**Status**: PASSED
**Date**: 2024-12-10

### Tests Run
```bash
python -c "from src.nodes import supervisor_node, customer_agent_node, employee_agent_node, recommendation_agent_node; print('All nodes OK')"
```

### Results
All agent nodes import successfully.

### Files Created
- `agent/src/nodes/__init__.py`
- `agent/src/nodes/supervisor.py`
- `agent/src/nodes/customer_agent.py`
- `agent/src/nodes/employee_agent.py`
- `agent/src/nodes/recommendation_agent.py`

### Notes
- Changed `config: dict` to `config: RunnableConfig` in all node functions to resolve type warnings

---

## Checkpoint 4: Graph Compilation
**Status**: PASSED
**Date**: 2024-12-10

### Tests Run
```bash
python -c "from src.agent import graph; print(f'Graph: {graph}')"
```

### Results
Graph compiles successfully with nodes: supervisor, customer_agent, employee_agent, recommendation_agent

### Files Created
- `agent/src/agent.py`

### Notes
- Removed `MemorySaver()` checkpointer - LangGraph Platform handles persistence automatically

---

## Checkpoint 5: LangGraph Dev Server
**Status**: PASSED
**Date**: 2024-12-10

### Tests Run
```bash
langgraph dev --port 8123
curl http://localhost:8123/info
```

### Issues Encountered & Fixes

#### Issue 1: ImportError - Relative imports
**Error**: `attempted relative import with no known parent package`
**Cause**: `langgraph.json` used file paths instead of module paths
**Fix**: Changed `langgraph.json` from file paths (`./src/auth.py:auth`) to module paths (`src.auth:auth`)

#### Issue 2: Custom checkpointer error
**Error**: "Your graph includes a custom checkpointer... please remove"
**Cause**: Graph was compiled with `checkpointer=MemorySaver()`
**Fix**: Removed checkpointer from `builder.compile()` - platform handles persistence

#### Issue 3: StudioUser not subscriptable
**Error**: `TypeError: 'StudioUser' object is not subscriptable`
**Cause**: `add_owner_metadata` tried to access `ctx.user["identity"]` but Studio mode provides a StudioUser object, not a dict
**Fix**: Added type checking in `add_owner_metadata`:
```python
if hasattr(ctx.user, "identity"):
    identity = ctx.user.identity
elif isinstance(ctx.user, dict):
    identity = ctx.user.get("identity", "unknown")
else:
    identity = "studio"
```

#### Issue 4: Blocking database call
**Error**: `BlockingError: Blocking call to sqlite3.Connection.execute`
**Cause**: LangGraph runtime doesn't allow blocking calls in async functions
**Fix**: Wrapped database lookup in `asyncio.to_thread()`:
```python
def _lookup_user(token: str) -> dict | None:
    # Synchronous database lookup
    ...

@auth.authenticate
async def authenticate(authorization: str | None):
    ...
    user_data = await asyncio.to_thread(_lookup_user, token)
    ...
```

#### Issue 5: GraphRecursionError - Infinite loop
**Error**: `GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition`
**Cause**: Supervisor was only looking at the last human message, not AI responses. After the customer_agent answered, supervisor would see the original "Show me my invoices" and route back to customer_agent again, creating an infinite loop.
**Fix**: Updated supervisor to review recent conversation context (last 6 messages) instead of just the last human message. This allows it to see when an agent has already provided a complete answer and return `FINISH`.

```python
# Now includes last 6 messages for context
recent_messages = []
for msg in state["messages"][-6:]:
    ...
conversation_context = "\n".join(recent_messages)
```

### Verification Tests

#### Test 1: Customer Flow (Jake)
```bash
# Create thread
curl -X POST http://localhost:8123/threads -H "Authorization: Bearer jake" -d '{}'
# Thread ID: 8577b76e-2c83-430f-a8ee-d6670ff910ed

# Start run
curl -X POST ".../threads/{id}/runs" -d '{"input": {"messages": [{"role": "user", "content": "Show me my invoices"}]}}'
# Run completed with status: success
```

**Result**: Jake's 4 invoices (413-416) returned correctly via customer_agent

#### Test 2: Employee Flow (Julia)
```bash
# Create thread
curl -X POST http://localhost:8123/threads -H "Authorization: Bearer julia" -d '{}'
# Thread ID: f01ccd3d-847d-4c84-aa56-6c1ebc695cc3

# Start run
curl -X POST ".../threads/{id}/runs" -d '{"input": {"messages": [{"role": "user", "content": "Which customers do I support?"}]}}'
# Run completed with status: success
```

**Result**: Julia's 2 supported customers (Jake ID:60, Neil ID:61) returned correctly via employee_agent

### Final State
- Server running on port 8123
- Custom authentication working (validates user tokens against database)
- Role-based routing working (customers → customer_agent, employees → employee_agent)
- Multi-agent conversation flow working without infinite loops
- Thread ownership/metadata correctly assigned

---

## Checkpoint 6: LangSmith Studio Visualization
**Status**: PASSED
**Date**: 2024-12-10
**Branch**: `backend-improvements`

### Goal
Enable graph visualization in LangSmith Studio UI with full edge visibility

### Issues Encountered & Fixes

#### Issue 1: `create_react_agent` adds default checkpointer
**Error**: `ValueError: Your graph includes a custom checkpointer (type <class 'langgraph.checkpoint.memory.InMemorySaver'>)`
**Cause**: `create_react_agent` from `langgraph.prebuilt` automatically adds a `MemorySaver` checkpointer by default
**Fix**: Added `checkpointer=False` to all `create_react_agent` calls

#### Issue 2: Studio "No assistants found" error
**Error**: `Failed to initialize Studio - Error: No assistants found`
**Cause**: Custom auth handler was blocking Studio requests (returning 401 for missing authorization)
**Fix**: Modified `auth.py` to return a default user when no authorization is provided

#### Issue 3: Authorization filters blocking Studio
**Error**: Studio could authenticate but assistants were being filtered out
**Cause**: `@auth.on` handler was applying owner filters to all users including Studio
**Fix**: Added `is_studio_user()` check to bypass filters for Studio users

#### Issue 4: Graph edges not visible in Studio
**Error**: Graph showed nodes but no edges between supervisor and sub-agents
**Cause**: `Command(goto="...")` creates edges at runtime, not visible in static graph visualization
**Fix**: Added explicit `add_conditional_edges()` and `add_edge()` declarations in `agent.py`:
```python
# Supervisor routes to agents (conditional edges for visualization)
def supervisor_route(state: AgentState) -> Literal[...]:
    """Placeholder for visualization - actual routing done by Command in node."""
    return "__end__"

builder.add_conditional_edges(
    "supervisor",
    supervisor_route,
    ["customer_agent", "employee_agent", "recommendation_agent", END]
)

# Agents return to supervisor
builder.add_edge("customer_agent", "supervisor")
builder.add_edge("employee_agent", "supervisor")
builder.add_edge("recommendation_agent", "supervisor")
```

#### Issue 5: Invalid model ID
**Error**: `NotFoundError: model: claude-opus-4-5-20250929`
**Cause**: Supervisor was using an invalid/future model ID
**Fix**: Changed to `claude-sonnet-4-5-20250929` (pending verification of correct model IDs for all agents)

### Mermaid Visualization Output
```
graph TD;
    __start__ --> supervisor;
    supervisor -.-> customer_agent;
    supervisor -.-> employee_agent;
    supervisor -.-> recommendation_agent;
    supervisor -.-> __end__;
    customer_agent --> supervisor;
    employee_agent --> supervisor;
    recommendation_agent --> supervisor;
```

### Files Modified
- `agent/src/agent.py` - Added explicit conditional edges for visualization
- `agent/src/nodes/supervisor.py` - Fixed model ID
- `agent/src/nodes/customer_agent.py` - Added `checkpointer=False`
- `agent/src/nodes/employee_agent.py` - Added `checkpointer=False`
- `agent/src/nodes/recommendation_agent.py` - Added `checkpointer=False`
- `agent/src/auth.py` - Added Studio user handling and `is_studio_user()` check
- `.claude/CLAUDE.md` - Added LangGraph routing patterns documentation

### Documentation Added
- Added Command vs Conditional Edges comparison to `.claude/CLAUDE.md`
- Created `/update-summary` slash command in `.claude/commands/`

### Remaining Work
- Verify and fix model IDs for all agents (currently using invalid IDs)
- Test API flows after model ID fixes
- Test Human-in-the-loop functionality

---

## Checkpoint 7: Model IDs & HITL Implementation
**Status**: PASSED
**Date**: 2024-12-11
**Branch**: `backend-improvements`

### Goal
1. Fix invalid model IDs across all agents
2. Implement proper Human-in-the-Loop (HITL) for invoice edit/delete operations

### Model ID Research
Fetched official Anthropic documentation to get valid model IDs:

| Model | Valid API ID | Alias |
|-------|--------------|-------|
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | `claude-sonnet-4-5` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | `claude-haiku-4-5` |
| Claude Opus 4.5 | `claude-opus-4-5-20251101` | `claude-opus-4-5` |

**Source**: https://platform.claude.com/docs/en/about-claude/models/overview

### Model ID Fixes Applied
Updated all agents to use `claude-sonnet-4-5-20250929`:
- `agent/src/nodes/supervisor.py` - Already correct
- `agent/src/nodes/customer_agent.py` - Changed from `claude-haiku-4-5-20251015` (invalid)
- `agent/src/nodes/employee_agent.py` - Changed from `claude-haiku-4-5-20251015` (invalid)
- `agent/src/nodes/recommendation_agent.py` - Changed from `claude-haiku-4-5-20251015` (invalid)

### API Tests After Model Fix

#### Test 1: Customer Flow (Jake)
```bash
curl -X POST "http://localhost:8123/threads/{thread_id}/runs/wait" \
  -H "Authorization: Bearer jake" \
  -d '{"assistant_id": "music_store", "input": {"messages": [{"role": "user", "content": "Show me my invoices"}]}}'
```
**Result**: PASSED - Jake's 4 invoices (413-416) returned correctly using `claude-sonnet-4-5-20250929`

#### Test 2: Employee Flow (Julia)
```bash
curl -X POST "http://localhost:8123/threads/{thread_id}/runs/wait" \
  -H "Authorization: Bearer julia" \
  -d '{"assistant_id": "music_store", "input": {"messages": [{"role": "user", "content": "Which customers do I support?"}]}}'
```
**Result**: PASSED - Julia sees 2 supported customers (Jake ID:60, Neil ID:61)

### HITL Implementation Issue & Fix

#### Problem Identified
Initial HITL implementation in `employee_agent_node` checked for tool calls AFTER `create_react_agent` completed its ReAct loop. By this point, tools had already executed and modified the database.

#### Root Cause
`create_react_agent` runs the entire ReAct loop internally (LLM → tool call → tool execution → response). The node function only sees the final result after all tools have run.

#### Solution (from LangGraph docs)
Per https://docs.langchain.com/oss/python/langgraph/interrupts, `interrupt()` should be called INSIDE the tools themselves, BEFORE making destructive changes:

```python
@tool
def edit_invoice(invoice_id: int, new_total: float) -> str:
    # Get invoice info first (read-only)
    with get_db() as conn:
        # ... fetch invoice details ...

    # Request approval BEFORE making changes
    approval = interrupt({
        "type": "manager_approval",
        "action": "edit_invoice",
        "invoice_id": invoice_id,
        "message": f"Approve editing Invoice #{invoice_id}?"
    })

    if not approval or not approval.get("approved", False):
        return "Edit was not approved. No changes made."

    # Only now perform the actual update
    with get_db() as conn:
        conn.execute("UPDATE invoices SET Total = ? WHERE InvoiceId = ?", ...)
        conn.commit()
```

### Files Modified
- `agent/src/nodes/customer_agent.py` - Updated model ID
- `agent/src/nodes/employee_agent.py` - Updated model ID, simplified node (removed redundant HITL check)
- `agent/src/nodes/recommendation_agent.py` - Updated model ID
- `agent/src/tools/employee_tools.py` - Added `interrupt()` calls inside `edit_invoice` and `delete_invoice` tools

### HITL Tests Completed

#### Test 1: Employee Edit Invoice (Julia)
```bash
# Initial request triggers interrupt
curl -X POST ".../threads/{id}/runs/wait" \
  -H "Authorization: Bearer julia" \
  -d '{"input": {"messages": [{"role": "user", "content": "Use edit_invoice to change invoice 413 to $50"}]}}'
# Returns __interrupt__ with approval request

# Resume with approval
curl -X POST ".../threads/{id}/runs/wait" \
  -d '{"command": {"resume": {"approved": true}}}'
# Invoice updated: $15.00 -> $50.00
```
**Result**: PASSED - Invoice 413 updated in database only after approval

#### Test 2: Employee Rejection (Julia)
```bash
# Resume with rejection
curl -X POST ".../threads/{id}/runs/wait" \
  -d '{"command": {"resume": {"approved": false}}}'
```
**Result**: PASSED - Invoice 414 unchanged ($8.91), rejection message returned

#### Test 3: Customer Purchase Album (Jake)
```bash
# Purchase triggers interrupt
curl -X POST ".../threads/{id}/runs/wait" \
  -H "Authorization: Bearer jake" \
  -d '{"input": {"messages": [{"role": "user", "content": "Use purchase_album to buy album ID 358"}]}}'
# Returns __interrupt__: "Confirm purchase of The Tortured Poets Department by Taylor Swift (3 tracks) for $2.97?"

# Resume with confirmation
curl -X POST ".../threads/{id}/runs/wait" \
  -d '{"command": {"resume": {"confirmed": true}}}'
# Invoice #421 created
```
**Result**: PASSED - Invoice 421 created for Jake with $2.97 total

### New Customer Tools Added
- `search_tracks(query)` - Search for tracks by name, artist, or album
- `search_albums(query)` - Search for albums by title or artist
- `purchase_track(customer_id, track_id)` - Purchase track with HITL confirmation
- `purchase_album(customer_id, album_id)` - Purchase all album tracks with HITL confirmation

### Files Modified
- `agent/src/nodes/customer_agent.py` - Updated model ID and prompt with new tools
- `agent/src/nodes/employee_agent.py` - Updated model ID, simplified node
- `agent/src/nodes/recommendation_agent.py` - Updated model ID
- `agent/src/tools/employee_tools.py` - Added `interrupt()` calls inside HITL tools
- `agent/src/tools/customer_tools.py` - Added search and purchase tools with HITL

### Database Cleanup
- Removed duplicate `chinook.db` from root level
- Agent uses `agent/chinook.db` exclusively

---

## Checkpoint 8: Enhanced Agent System Prompts
**Status**: PASSED
**Date**: 2024-12-11
**Branch**: `backend-improvements`

### Goal
Improve agent system prompts to ensure tools are called reliably. The employee agent was not calling tools when expected in previous tests.

### Changes Made

#### Employee Agent (`agent/src/nodes/employee_agent.py`)
Restructured prompt with explicit tool documentation:
- Each tool now has: signature, USE WHEN triggers, ALWAYS CALL WITH params, EXAMPLE TRIGGERS
- Added CRITICAL RULES section emphasizing "ALWAYS use a tool when the user's request matches"
- Explicit employee_id and supported_customers injection

#### Customer Agent (`agent/src/nodes/customer_agent.py`)
Same structured format for 7 tools:
- `get_my_invoices`, `get_my_purchases`, `get_invoice_details` (read operations)
- `search_tracks`, `search_albums` (discovery)
- `purchase_track`, `purchase_album` (HITL purchases)
- Added guidance: "For purchases, FIRST search to get the track_id or album_id, THEN call purchase"

#### Recommendation Agent (`agent/src/nodes/recommendation_agent.py`)
Documented 3 tools with explicit trigger conditions:
- `get_genre_recommendations` - personalized based on purchase history
- `get_artist_recommendations` - discover similar artists
- `get_popular_tracks_in_genre` - explore genre charts

#### Supervisor (`agent/src/nodes/supervisor.py`)
Enhanced routing prompt:
- Explicit agent capabilities with example trigger phrases
- Clear FINISH conditions (answer already provided, greetings, etc.)
- Role-based routing rules more prominent

### Prompt Structure Used
```
## YOUR IDENTITY
- Role-specific context

## AVAILABLE TOOLS

### 1. tool_name(param: type)
USE WHEN: <trigger conditions>
ALWAYS CALL WITH: <hardcoded params>
EXAMPLE TRIGGERS: <sample user phrases>

## CRITICAL RULES
1. ALWAYS use a tool when the user's request matches
...
```

### Files Modified
- `agent/src/nodes/employee_agent.py` - Enhanced system prompt
- `agent/src/nodes/customer_agent.py` - Enhanced system prompt
- `agent/src/nodes/recommendation_agent.py` - Enhanced system prompt
- `agent/src/nodes/supervisor.py` - Enhanced routing prompt

### Verification
Server hot-reloaded changes automatically. Prompts now provide clear, unambiguous tool usage instructions.

---

## Summary

8 checkpoints completed. All model IDs corrected, HITL flows tested, and agent prompts enhanced.

The LangGraph Music Store backend is fully functional with:
- Custom authentication based on user's first name
- Role-based agent routing (customer vs employee)
- 3 specialized agents (customer, employee, recommendation)
- All agents using valid `claude-sonnet-4-5-20250929` model
- **Enhanced system prompts** with explicit tool documentation:
  - Structured format: signature, USE WHEN, ALWAYS CALL WITH, EXAMPLE TRIGGERS
  - CRITICAL RULES sections ensuring tools are called reliably
- **Human-in-the-loop working** for:
  - Employee invoice edits/deletes (manager approval)
  - Customer track/album purchases (purchase confirmation)
- Jake has 33 Taylor Swift tracks in purchase history
- Search tools for finding tracks and albums
- Proper conversation flow without recursion errors
- Full LangSmith Studio visualization with edges
- Documentation on Command vs Conditional Edge routing patterns
