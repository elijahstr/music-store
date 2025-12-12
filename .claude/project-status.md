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
- **Model**: `claude-sonnet-4-5-20250929` for all agents

### Agents
| Agent | Purpose | Tools |
|-------|---------|-------|
| Supervisor | Routes requests based on user role and intent | N/A |
| Customer Agent | Invoice queries, purchases, search | get_my_invoices, get_my_purchases, search_tracks, search_albums, purchase_track, purchase_album |
| Employee Agent | Customer management, invoice edits | get_employee_info, get_supported_customers, get_customer_invoices, edit_invoice, delete_invoice |
| Recommendation Agent | Music recommendations | get_genre_recommendations, get_artist_recommendations, get_popular_tracks_in_genre |

### Human-in-the-Loop (HITL)
- **Employee**: Invoice edit/delete requires manager approval
- **Customer**: Track/album purchases require confirmation
- Implemented via `interrupt()` inside tool functions

### Key Files
```
agent/
├── src/
│   ├── agent.py          # Graph definition
│   ├── auth.py           # Custom authentication (includes debug logging)
│   ├── state.py          # AgentState definition
│   ├── db.py             # Database connection helper
│   ├── utils.py          # Auth utility with multi-source fallback
│   ├── nodes/
│   │   ├── supervisor.py
│   │   ├── customer_agent.py
│   │   ├── employee_agent.py
│   │   └── recommendation_agent.py
│   └── tools/
│       ├── customer_tools.py
│       ├── employee_tools.py
│       └── recommendation_tools.py
├── langgraph.json
└── chinook.db            # SQLite database
```

### Running Backend
```bash
cd agent && source .venv/bin/activate && langgraph dev --port 8123
```

---

## Streamlit Frontend Status: COMPLETE

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
├── app.py                    # Main Streamlit chat application
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
| "Buy track 3503" | Triggers purchase confirmation dialog |

### Employee Tests (as Julia)
| Query | Expected |
|-------|----------|
| "Show me my employee info" | Returns Julia's profile |
| "Which customers do I support?" | Lists Jake and Neil |
| "Show me Jake's invoices" | Returns Jake's invoices |
| "Edit invoice 413, change total to $25" | Triggers manager approval dialog |

---

## Issues Resolved During Development

### Backend Issues
1. **Relative imports** - Changed langgraph.json to use module paths
2. **Checkpointer conflicts** - Removed custom checkpointer (platform handles it)
3. **StudioUser type** - Added type checking for Studio vs API users
4. **Blocking DB calls** - Wrapped in `asyncio.to_thread()`
5. **Infinite recursion** - Supervisor now reviews last 6 messages for context
6. **Invalid model IDs** - Updated all agents to valid `claude-sonnet-4-5-20250929`
7. **HITL timing** - Moved `interrupt()` inside tools, before destructive operations

### Frontend Issues (Session 2025-12-11)
1. **CopilotKit removed** - Deleted entire `frontend/` directory (Next.js + CopilotKit had auth issues)
2. **Dark mode detection** - Streamlit respects system dark mode; added `base = "light"` to config.toml
3. **Text visibility** - Added explicit color rules for all text elements to ensure contrast
4. **Chat input styling** - Custom CSS for white background, teal borders on chat input
5. **Focus states** - Overrode default red focus color with teal (`#2F6868`)

---

## Remaining Work

- [ ] Test HITL flows in Streamlit (purchase confirmation, manager approval)
- [ ] Improve response latency (currently slow due to multi-agent routing)
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

### Backend Auth Verification
Direct API calls with Authorization header work correctly:
```bash
curl -X POST http://localhost:8123/runs/stream \
  -H "Authorization: Bearer jake" \
  -H "Content-Type: application/json" \
  -d '{"assistant_id":"music_store","input":{"messages":[{"role":"human","content":"Hello"}]}}'
```
Logs show: `[AUTH UTIL] Using langgraph_auth_user: Jake Broekhuizen (customer)`

### Streamlit + LangGraph SDK Integration
Key pattern for passing auth headers:
```python
from langgraph_sdk import get_sync_client

client = get_sync_client(
    url="http://localhost:8123",
    headers={"Authorization": f"Bearer {username}"},
)
```

### LangGraph 0.6.0+ Context Change
- `configurable` is being replaced by `context` in LangGraph 0.6.0+
- Cannot use both simultaneously (causes HTTP 400 error)
- Streamlit approach avoids this by using HTTP headers directly

---

## Session Work Log (2025-12-11)

### Completed This Session
- [x] Removed all CopilotKit code (deleted `frontend/` directory)
- [x] Cleaned up CopilotKit references from `agent/src/utils.py`
- [x] Updated project documentation to remove CopilotKit sections
- [x] Added traditional login flow to Streamlit (username/password with `demo123`)
- [x] Implemented LangChain brand colors (teal theme: `#2F6868`, `#84C4C0`, `#1C3C3C`)
- [x] Added `.streamlit/config.toml` with light theme configuration
- [x] Fixed dark mode issues with explicit white backgrounds
- [x] Styled chat messages with borders and padding
- [x] Styled chat input box with teal border and shadow
- [x] Fixed text visibility issues (demo accounts, captions)
- [x] Changed focus highlight color from red to teal
- [x] Renamed app to "The Music Company Of San Francisco"
- [x] Added top gradient accent bar
