# LangGraph Music Store Demo - Project Status

## Overview

Multi-agent music store demo using LangGraph (backend) with Streamlit frontend.
**App Name**: The Music Company Of San Francisco

---

## Demo Users

| Person | Token | Role | Password |
|--------|-------|------|----------|
| Jake Broekhuizen | `jake` | Customer | `demo123` |
| Neil Dahlke | `neil` | Customer | `demo123` |
| Julia Schottenstein | `julia` | Employee (Sales Support Manager) | `demo123` |

---

## Backend Status: COMPLETE

### Architecture
- **Graph ID**: `music_store`
- **Auth**: Custom token-based (Bearer {first_name})
- **Model**: `claude-haiku-4-5-20251001` for all agents (updated for speed)

### Agents
| Agent | Purpose | Tools |
|-------|---------|-------|
| Supervisor | Routes requests based on user role and intent | N/A |
| Customer Agent | Invoice queries, purchases, search | get_my_invoices, get_my_purchases, search_tracks, search_albums, purchase_track, purchase_album |
| Employee Agent | Customer management, invoice edits | get_employee_info, get_supported_customers, get_customer_invoices, edit_invoice, delete_invoice |
| Recommendation Agent | Music recommendations | get_genre_recommendations, get_artist_recommendations, get_popular_tracks_in_genre |

### Human-in-the-Loop (HITL)
- **Employee**: Invoice edit/delete requires manager approval (`approved` key)
- **Customer**: Track/album purchases require confirmation (`confirmed` key)
- Implemented via `interrupt()` inside tool functions
- **Status**: Frontend UI added, but interrupt detection from stream needs debugging

### Latency Optimizations (Session 2025-12-12)
- Added `supervisor_turns` counter to state to prevent infinite agent loops
- `MAX_SUPERVISOR_TURNS = 2` forces exit after 2 supervisor invocations per request
- Counter resets on each new human message (not per thread)
- Updated supervisor prompt to prefer FINISH over unnecessary routing

### Key Files
```
agent/
├── src/
│   ├── agent.py          # Graph definition
│   ├── auth.py           # Custom authentication (includes debug logging)
│   ├── state.py          # AgentState definition (includes supervisor_turns)
│   ├── db.py             # Database connection helper
│   ├── utils.py          # Auth utility with multi-source fallback
│   ├── nodes/
│   │   ├── supervisor.py       # MAX_SUPERVISOR_TURNS=2, turn tracking
│   │   ├── customer_agent.py   # claude-haiku-4-5-20251001
│   │   ├── employee_agent.py   # claude-haiku-4-5-20251001
│   │   └── recommendation_agent.py  # claude-haiku-4-5-20251001
│   └── tools/
│       ├── customer_tools.py   # purchase_track/album with interrupt()
│       ├── employee_tools.py   # edit/delete_invoice with interrupt()
│       └── recommendation_tools.py  # get_popular_tracks_in_genre now excludes owned tracks
├── langgraph.json
└── chinook.db            # SQLite database
```

### Running Backend
```bash
cd agent && source .venv/bin/activate && langgraph dev --port 8123
```

---

## Streamlit Frontend Status: IN PROGRESS

### Tech Stack
- Streamlit 1.40+
- LangGraph SDK (langgraph-sdk)
- Python 3.12

### Features Implemented
- **Traditional login flow** with username/password authentication
- Auth header forwarding to LangGraph backend via `langgraph_sdk`
- Chat interface with message history
- Real-time status updates showing which node is executing
- Thread persistence across messages
- Logout functionality
- **LangChain-branded UI** with custom teal color scheme
- **HITL confirmation UI** - Confirm/Cancel buttons for interrupts (added 2025-12-12)
- **Auto-focus chat input** - Chat input automatically focused after login (added 2025-12-11)
- **Auto-scroll to interrupt dialog** - Page scrolls to confirmation dialog instead of jumping to top
- **Denial acknowledgement** - Shows "Action cancelled" or "Request denied" when user denies HITL prompt

### HITL UI Implementation (Session 2025-12-12)
- Added `pending_interrupt` to session state
- `stream_response_with_status()` now detects `__interrupt__` events in stream
- Confirmation dialog shows with Approve/Deny or Confirm/Cancel buttons
- Uses correct resume key based on interrupt type (`approved` vs `confirmed`)
- Resume uses `command={"resume": value}` to continue interrupted runs

### UI Theming (LangChain Colors)
- Primary: `#2F6868` (teal)
- Light accent: `#84C4C0`
- Dark accent: `#1C3C3C`
- Backgrounds: White (`#ffffff`) and light gray (`#f4f6f6`)
- Top gradient accent bar
- Custom styled chat messages with borders
- Teal focus states on input fields

### Key Files
```
streamlit_app/
├── app.py                    # Main Streamlit chat application (HITL handling added)
├── requirements.txt          # Dependencies (streamlit, langgraph-sdk)
└── .streamlit/
    └── config.toml           # Theme configuration (light mode, teal primary)
```

### Running Streamlit Frontend
```bash
cd agent && source .venv/bin/activate
streamlit run ../streamlit_app/app.py --server.port 8501
```

Access: http://localhost:8501 (add `?embed_options=light_theme` if dark mode issues)

---

## Test Scenarios

### Customer Tests (as Jake or Neil)
| Query | Expected |
|-------|----------|
| "Show me my invoices" | Returns user's invoices |
| "What music have I bought?" | Shows purchased tracks |
| "Search for rock music" | Returns matching tracks |
| "Buy track 1" | Should trigger purchase confirmation dialog (HITL) |
| "Top rock songs" | Returns popular tracks excluding already-owned |

### Employee Tests (as Julia)
| Query | Expected |
|-------|----------|
| "Show me my employee info" | Returns Julia's profile |
| "Which customers do I support?" | Lists Jake and Neil |
| "Show me Jake's invoices" | Returns Jake's invoices |
| "Edit invoice 413, change total to $25" | Should trigger manager approval dialog (HITL) |

---

## Issues Resolved During Development

### Backend Issues
1. **Relative imports** - Changed langgraph.json to use module paths
2. **Checkpointer conflicts** - Removed custom checkpointer (platform handles it)
3. **StudioUser type** - Added type checking for Studio vs API users
4. **Blocking DB calls** - Wrapped in `asyncio.to_thread()`
5. **Infinite recursion** - Supervisor now reviews last 6 messages for context
6. **Invalid model IDs** - Updated all agents to valid model IDs
7. **HITL timing** - Moved `interrupt()` inside tools, before destructive operations

### Latency Issues (Session 2025-12-12)
8. **Infinite supervisor loops** - Added `supervisor_turns` counter with MAX=2
9. **Turn counter persisting across thread** - Now resets on each new human message
10. **Slow model** - Changed from `claude-sonnet-4-5-20250929` to `claude-haiku-4-5-20251001`
11. **Unnecessary routing** - Updated supervisor prompt to prefer FINISH aggressively

### Frontend Issues (Session 2025-12-11)
1. **CopilotKit removed** - Deleted entire `frontend/` directory (Next.js + CopilotKit had auth issues)
2. **Dark mode detection** - Streamlit respects system dark mode; added `base = "light"` to config.toml
3. **Text visibility** - Added explicit color rules for all text elements to ensure contrast
4. **Chat input styling** - Custom CSS for white background, teal borders on chat input
5. **Focus states** - Overrode default red focus color with teal (`#2F6868`)

### Frontend Issues (Session 2025-12-12)
6. **pending_interrupt not initialized** - Added separate initialization check for existing sessions
7. **HITL interrupt detection** - Updated to look for `__interrupt__` in stream updates
8. **Chat input not focused after login** - Added `components.html` with JavaScript to auto-focus chat input via `window.parent.document`
9. **Page jumping to top on interrupt** - Added anchor element and auto-scroll JavaScript to keep view at confirmation dialog
10. **No denial acknowledgement** - Added fallback message when user cancels/denies HITL prompt

### Backend Issues (Session 2025-12-11)
12. **Agent mentions "system issues" on cancellation** - Updated customer_agent and employee_agent prompts to handle denials gracefully without mentioning errors

---

## Remaining Work

- [ ] **Debug HITL interrupt flow** - Interrupts not triggering in Streamlit (tool may not be called, or interrupt not bubbling up from react agent)
- [ ] Add token streaming for real-time response display
- [ ] Deploy to LangGraph Platform (optional)
- [ ] Add error handling for backend connection failures

---

## Technical Notes

### Auth Flow (Streamlit - Working)

```
Streamlit Frontend:
  └── get_sync_client(url, headers={"Authorization": f"Bearer {user}"})
       ↓
LangGraph Backend (port 8123):
  ├── auth.authenticate() receives "Bearer jake" header
  ├── Looks up user in chinook.db
  └── Returns user dict with role, permissions, etc.
       ↓
Agent Nodes:
  └── get_auth_user(config) extracts user from config.configurable.langgraph_auth_user
```

### Supervisor Turn Tracking

```python
# In supervisor_node():
# Reset counter if last message is from human (new user request)
is_new_request = last_msg.type == "human"
current_turns = 0 if is_new_request else state.get("supervisor_turns", 0)

# Force exit if max turns reached
if current_turns >= MAX_SUPERVISOR_TURNS:  # MAX = 2
    return Command(goto="__end__")
```

### HITL Resume Pattern (Streamlit)

```python
# Resume with confirmation
client.runs.stream(
    thread_id=thread_id,
    assistant_id=ASSISTANT_ID,
    input=None,
    command={"resume": {"confirmed": True}},  # or {"approved": True} for employee
    stream_mode=["values", "updates"],
)
```

### Recommendation Tools - Owned Track Exclusion

`get_popular_tracks_in_genre` now accepts optional `customer_id` to exclude already-owned tracks:
```python
@tool
def get_popular_tracks_in_genre(genre_name: str, customer_id: int = None) -> str:
    # If customer_id provided, excludes tracks they already own
```

---

## Session Work Log (2025-12-12)

### Completed This Session
- [x] Added `supervisor_turns` counter to AgentState for latency control
- [x] Implemented MAX_SUPERVISOR_TURNS=2 with forced exit
- [x] Turn counter resets on each new human message (not per thread)
- [x] Changed all agents from Sonnet to Haiku (`claude-haiku-4-5-20251001`)
- [x] Updated supervisor prompt to prefer FINISH over unnecessary routing
- [x] Added HITL confirmation UI to Streamlit frontend
- [x] Added `pending_interrupt` session state with proper initialization
- [x] Updated `stream_response_with_status()` to detect `__interrupt__` events
- [x] Implemented Confirm/Cancel buttons with correct resume keys
- [x] Updated `get_popular_tracks_in_genre` to exclude owned tracks via customer_id parameter
- [x] Added debug logging to `purchase_track` tool

### In Progress
- [ ] Debugging why HITL interrupts don't trigger (purchase_track tool may not be called by Haiku)

### Branch
Working on `latency-improvements` branch

---

## Session Work Log (2025-12-11)

### Completed This Session
- [x] Auto-focus chat input after login using `streamlit.components.v1.html` with JavaScript
- [x] Auto-scroll to interrupt confirmation dialog (prevents page jumping to top on rerun)
- [x] Added denial acknowledgement fallback message in frontend
- [x] Updated customer_agent prompt - rule #6: handle cancellations without mentioning system issues
- [x] Updated employee_agent prompt - rule #6: handle manager denials gracefully

### Key Changes
- **streamlit_app/app.py**: Added `import streamlit.components.v1 as components`, auto-focus script, interrupt dialog anchor with scroll-to script, denial fallback message
- **agent/src/nodes/customer_agent.py**: Added rule about cancellation messaging
- **agent/src/nodes/employee_agent.py**: Added rule about denial messaging
