# LangGraph Music Store Backend - Implementation Plan

> This plan serves as reference documentation for the implementation of the LangGraph multi-agent backend.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                 BACKEND (LangGraph Platform)                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Auth Handler                           │  │
│  │  - Validates token (user's first name)                    │  │
│  │  - Returns: role, employee_id/customer_id, supported_customers │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   SUPERVISOR                              │  │
│  │  - Checks user role from auth context                     │  │
│  │  - Routes to appropriate agent based on role + intent     │  │
│  │  - Customers → customer_agent or recommendation_agent     │  │
│  │  - Employees → employee_agent or recommendation_agent     │  │
│  └───────────────────────────────────────────────────────────┘  │
│           │                    │                    │           │
│           ▼                    ▼                    ▼           │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │  Customer   │    │    Employee     │    │ Recommendation  │ │
│  │   Agent     │    │     Agent       │    │     Agent       │ │
│  │             │    │                 │    │                 │ │
│  │ Tools:      │    │ Tools:          │    │ Tools:          │ │
│  │ -get_my_    │    │ -get_employee_  │    │ -get_genre_     │ │
│  │  invoices   │    │  info           │    │  recommendations│ │
│  │ -get_my_    │    │ -get_supported_ │    │ -get_artist_    │ │
│  │  purchases  │    │  customers      │    │  recommendations│ │
│  │ -get_invoice│    │ -get_customer_  │    │ -get_popular_   │ │
│  │  _details   │    │  invoices       │    │  tracks_in_genre│ │
│  │             │    │ -edit_invoice   │    │                 │ │
│  │             │    │  (HITL)         │    │                 │ │
│  │             │    │ -delete_invoice │    │                 │ │
│  │             │    │  (HITL)         │    │                 │ │
│  └─────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Demo Users (In Database)

| Person | Role | ID | Details |
|--------|------|-----|---------|
| **Julia Schottenstein** | Employee | EmployeeId: 9 | Sales Support Agent, supports Jake & Neil |
| **Jake Broekhuizen** | Customer | CustomerId: 60 | 4 invoices (413-416), supported by Julia |
| **Neil Dahlke** | Customer | CustomerId: 61 | 4 invoices (417-420), supported by Julia |

---

## Project Structure

```
agent/
├── src/
│   ├── __init__.py
│   ├── agent.py                    # Main graph composition
│   ├── state.py                    # Shared state definition
│   ├── auth.py                     # Custom auth handler
│   ├── db.py                       # SQLite helpers
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── supervisor.py           # Supervisor/router node
│   │   ├── customer_agent.py       # Customer agent node
│   │   ├── employee_agent.py       # Employee agent node (with HITL)
│   │   └── recommendation_agent.py # Recommendation agent node
│   └── tools/
│       ├── __init__.py
│       ├── customer_tools.py       # Customer query tools
│       ├── employee_tools.py       # Employee query tools
│       └── recommendation_tools.py # Music recommendation tools
├── langgraph.json                  # LangGraph Platform config
├── pyproject.toml                  # Python dependencies
├── .env                            # Environment variables
└── chinook.db                      # SQLite database
```

---

## Implementation Phases

### Phase 1: Project Setup
- Create directory structure
- Create `pyproject.toml` with dependencies
- Create `langgraph.json` platform config
- Copy `chinook.db` to agent directory

### Phase 2: Core Modules
- `db.py` - Database connection helper
- `state.py` - AgentState definition
- `auth.py` - Custom auth handler

### Phase 3: Tools
- Customer tools: `get_my_invoices`, `get_my_purchases`, `get_invoice_details`
- Employee tools: `get_employee_info`, `get_supported_customers`, `get_customer_invoices`, `edit_invoice`, `delete_invoice`
- Recommendation tools: `get_genre_recommendations`, `get_artist_recommendations`, `get_popular_tracks_in_genre`

### Phase 4: Agent Nodes
- Supervisor node (routes based on role + intent)
- Customer agent node (ReAct with customer tools)
- Employee agent node (ReAct with employee tools + HITL)
- Recommendation agent node (ReAct with recommendation tools)

### Phase 5: Main Graph
- Compose StateGraph with all nodes
- START → supervisor → appropriate agent → back to supervisor or END
- Compile with MemorySaver checkpointer

---

## Test Checkpoints

> **IMPORTANT**: After completing each checkpoint, write a summary to `.claude/work-summary.md` documenting:
> - What was tested
> - Results (pass/fail)
> - Any errors encountered and fixes applied
> - Current state of the implementation

### Checkpoint 1: Core Modules
```bash
cd agent && uv pip install -e .
python -c "from src.db import get_db; print('DB OK')"
python -c "from src.state import AgentState; print('State OK')"
python -c "from src.auth import auth; print('Auth OK')"
```
**After completing**: Update `.claude/work-summary.md` with Phase 2 results.

### Checkpoint 2: Tools
```bash
python -c "from src.tools.customer_tools import get_my_invoices; print(get_my_invoices.invoke({'customer_id': 60}))"
python -c "from src.tools.employee_tools import get_employee_info; print(get_employee_info.invoke({'employee_id': 9}))"
python -c "from src.tools.recommendation_tools import get_popular_tracks_in_genre; print(get_popular_tracks_in_genre.invoke({'genre_name': 'Rock'}))"
```
**After completing**: Update `.claude/work-summary.md` with Phase 3 results.

### Checkpoint 3: Node Imports
```bash
python -c "from src.nodes import supervisor_node, customer_agent_node, employee_agent_node, recommendation_agent_node; print('All nodes OK')"
```
**After completing**: Update `.claude/work-summary.md` with Phase 4 results.

### Checkpoint 4: Graph Compilation
```bash
python -c "from src.agent import graph; print(f'Graph: {graph}')"
```
**After completing**: Update `.claude/work-summary.md` with Phase 5 results.

### Checkpoint 5: LangGraph Dev Server
```bash
langgraph dev --port 8123
```
Test endpoints:
- `curl http://localhost:8123/info` - Server info
- `curl -X POST http://localhost:8123/assistants/search` - List assistants
- Test auth with `Authorization: Bearer jake` or `julia`

**After completing**: Update `.claude/work-summary.md` with full integration test results.

---

## Key Implementation Notes

- All code follows the spec in `langgraph-music-store-plan.md`
- Tools have NO auth checks - auth is handled at agent level
- HITL uses `interrupt()` from `langgraph.types`
- Auth context accessed via `config["configurable"]["langgraph_auth_user"]`
- Using `claude-sonnet-4-20250514` model
- Use `uv` for Python package management

---

## Test Scenarios

### Customer Tests (as Jake or Neil)
| Query | Expected Behavior |
|-------|-------------------|
| "Show me my invoices" | Returns invoices 413-416 (Jake) or 417-420 (Neil) |
| "What music have I bought?" | Shows purchased tracks with artist/genre |
| "Give me details on invoice 413" | Shows line items for that invoice |
| "Recommend me some new music" | Analyzes purchase history, suggests similar tracks |

### Employee Tests (as Julia)
| Query | Expected Behavior |
|-------|-------------------|
| "Show me my employee info" | Returns Julia's profile |
| "Which customers do I support?" | Lists Jake and Neil with stats |
| "Show me Jake's invoices" | Returns Jake's 4 invoices |
| "Edit invoice 413, change total to 10.00" | Triggers HITL approval dialog |
| "Delete invoice 417" | Triggers HITL approval dialog |
