# LangGraph Music Store Demo - Implementation Plan

## Overview

Build a multi-persona chatbot for a digital music store demonstrating:
- **LangGraph Platform** deployment with **LangSmith** tracing
- **Supervisor/router** multi-agent architecture
- **Human-in-the-loop** (HITL) for invoice edit/delete operations
- **CopilotKit** frontend on **Vercel**
- **Role-based access** (employee vs customer)

---

## Demo Users (Already in Database)

| Person | Role | ID | Details |
|--------|------|-----|---------|
| **Julia Schottenstein** | Employee | EmployeeId: 9 | Sales Support Agent, supports Jake & Neil |
| **Jake Broekhuizen** | Customer | CustomerId: 60 | 4 invoices (413-416), supported by Julia |
| **Neil Dahlke** | Customer | CustomerId: 61 | 4 invoices (417-420), supported by Julia |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Vercel)                          │
│  Next.js + CopilotKit                                           │
│  - CopilotKit provider with agent="music_store"                 │
│  - useLangGraphInterrupt() for manager approval UI              │
│  - User selector (Julia/Jake/Neil) sets auth token              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
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
│  │ -get_my_    │    │ -get_supported_ │    │                 │ │
│  │  purchases  │    │  customers      │    │                 │ │
│  │             │    │ -get_customer_  │    │                 │ │
│  │             │    │  invoices       │    │                 │ │
│  │             │    │ -edit_invoice   │    │                 │ │
│  │             │    │  (HITL)         │    │                 │ │
│  │             │    │ -delete_invoice │    │                 │ │
│  │             │    │  (HITL)         │    │                 │ │
│  └─────────────┘    └─────────────────┘    └─────────────────┘ │
│                              │                                  │
│                     ┌────────┴────────┐                        │
│                     │   interrupt()   │                        │
│                     │ "Manager        │                        │
│                     │  Approval"      │                        │
│                     └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Chinook SQLite │
                    │    Database     │
                    └─────────────────┘
```

---

## Auth Model

Authorization is handled at the **agent level**, not tool level:

| Layer | Responsibility |
|-------|----------------|
| **Auth Handler** | Validates identity, returns role + IDs |
| **Supervisor** | Routes to agent based on role |
| **Agent** | Has role-appropriate tools, injects user IDs via prompt |
| **Tools** | Pure business logic, no auth checks |

---

## Project Structure

```
music-store-demo/
├── agent/                              # LangGraph backend
│   ├── src/
│   │   ├── __init__.py
│   │   ├── agent.py                    # Main graph composition
│   │   ├── state.py                    # Shared state definition
│   │   ├── auth.py                     # Custom auth handler
│   │   ├── db.py                       # SQLite helpers
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── supervisor.py           # Supervisor/router node
│   │   │   ├── customer_agent.py       # Customer agent node
│   │   │   ├── employee_agent.py       # Employee agent node (with HITL)
│   │   │   └── recommendation_agent.py # Recommendation agent node
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── customer_tools.py       # Customer query tools
│   │       ├── employee_tools.py       # Employee query tools
│   │       └── recommendation_tools.py # Music recommendation tools
│   ├── langgraph.json                  # LangGraph Platform config
│   ├── pyproject.toml                  # Python dependencies
│   ├── .env                            # Environment variables
│   └── chinook.db                      # SQLite database (copy here)
│
├── frontend/                           # Next.js + CopilotKit
│   ├── app/
│   │   ├── api/
│   │   │   └── copilotkit/
│   │   │       └── route.ts            # CopilotKit API route
│   │   ├── page.tsx                    # Main chat UI
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ChatInterface.tsx
│   │   └── UserSelector.tsx            # Demo user switcher
│   ├── package.json
│   ├── .env.local
│   ├── next.config.js
│   └── tsconfig.json
│
└── README.md
```

---

## Backend Implementation

### File: `agent/pyproject.toml`

```toml
[project]
name = "music-store-agent"
version = "0.1.0"
description = "Multi-agent music store demo"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langgraph-sdk>=0.1.0",
    "langchain-anthropic>=0.2.0",
    "langchain-core>=0.3.0",
]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

### File: `agent/langgraph.json`

```json
{
  "python_version": "3.11",
  "dependencies": ["."],
  "graphs": {
    "music_store": "./src/agent.py:graph"
  },
  "auth": {
    "path": "./src/auth.py:auth"
  },
  "env": ".env"
}
```

### File: `agent/.env`

```bash
ANTHROPIC_API_KEY=your-anthropic-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=music-store-demo
```

### File: `agent/src/__init__.py`

```python
# Empty init file
```

### File: `agent/src/db.py`

```python
"""Database connection helpers."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Database path relative to agent directory
DATABASE_PATH = Path(__file__).parent.parent / "chinook.db"


@contextmanager
def get_db():
    """Get a database connection with Row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

### File: `agent/src/state.py`

```python
"""Shared state definition for the multi-agent system."""

from typing import Literal, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """Extended state for multi-agent music store system."""
    
    # User context (set from auth)
    user_role: Literal["employee", "customer"]
    user_id: int  # employee_id or customer_id depending on role
    user_name: str
    supported_customers: list[int]  # For employees only, empty for customers
    
    # Routing
    next_agent: Optional[str]
```

### File: `agent/src/auth.py`

```python
"""Custom authentication handler for LangGraph Platform."""

from langgraph_sdk import Auth
from .db import get_db

auth = Auth()


@auth.authenticate
async def authenticate(authorization: str | None) -> Auth.types.MinimalUserDict:
    """
    Validate user token and return identity + context.
    
    For this demo, token is the user's first name (julia, jake, neil).
    In production, this would validate a real JWT/session token.
    """
    if not authorization:
        raise Auth.exceptions.HTTPException(
            status_code=401, 
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>" format
    token = authorization.replace("Bearer ", "").strip().lower()
    
    with get_db() as conn:
        # Check if token matches an employee
        cur = conn.execute("""
            SELECT EmployeeId, FirstName, LastName 
            FROM employees 
            WHERE LOWER(FirstName) = ?
        """, (token,))
        emp = cur.fetchone()
        
        if emp:
            # Get list of customers this employee supports
            cur = conn.execute(
                "SELECT CustomerId FROM customers WHERE SupportRepId = ?",
                (emp["EmployeeId"],)
            )
            supported_customers = [row["CustomerId"] for row in cur.fetchall()]
            
            return {
                "identity": token,
                "role": "employee",
                "employee_id": emp["EmployeeId"],
                "user_id": emp["EmployeeId"],
                "name": f"{emp['FirstName']} {emp['LastName']}",
                "supported_customers": supported_customers,
                "permissions": ["employee:read", "employee:write", "customer:read"],
            }
        
        # Check if token matches a customer
        cur = conn.execute("""
            SELECT CustomerId, FirstName, LastName 
            FROM customers 
            WHERE LOWER(FirstName) = ?
        """, (token,))
        cust = cur.fetchone()
        
        if cust:
            return {
                "identity": token,
                "role": "customer",
                "customer_id": cust["CustomerId"],
                "user_id": cust["CustomerId"],
                "name": f"{cust['FirstName']} {cust['LastName']}",
                "supported_customers": [],
                "permissions": ["customer:read"],
            }
    
    # No matching user found
    raise Auth.exceptions.HTTPException(
        status_code=401, 
        detail=f"Unknown user: {token}"
    )


@auth.on
async def add_owner_metadata(ctx: Auth.types.AuthContext, value: dict):
    """Add owner metadata to resources for filtering."""
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user["identity"]
    return {"owner": ctx.user["identity"]}
```

### File: `agent/src/tools/__init__.py`

```python
"""Tools package."""

from .customer_tools import CUSTOMER_TOOLS
from .employee_tools import EMPLOYEE_TOOLS, HITL_TOOLS
from .recommendation_tools import RECOMMENDATION_TOOLS

__all__ = [
    "CUSTOMER_TOOLS",
    "EMPLOYEE_TOOLS", 
    "HITL_TOOLS",
    "RECOMMENDATION_TOOLS",
]
```

### File: `agent/src/tools/customer_tools.py`

```python
"""Tools for customer queries. No auth checks - agent-level auth only."""

from langchain_core.tools import tool
from ..db import get_db


@tool
def get_my_invoices(customer_id: int) -> str:
    """
    Get all invoices for a customer.
    
    Args:
        customer_id: The customer's ID
    
    Returns:
        Formatted list of invoices with ID, date, and total
    """
    with get_db() as conn:
        cur = conn.execute("""
            SELECT InvoiceId, InvoiceDate, BillingCity, BillingCountry, Total 
            FROM invoices 
            WHERE CustomerId = ?
            ORDER BY InvoiceDate DESC
        """, (customer_id,))
        rows = cur.fetchall()
    
    if not rows:
        return "You have no invoices."
    
    lines = []
    for r in rows:
        lines.append(f"Invoice #{r['InvoiceId']} - {r['InvoiceDate']} - ${r['Total']:.2f} ({r['BillingCity']}, {r['BillingCountry']})")
    
    return "\n".join(lines)


@tool
def get_my_purchases(customer_id: int) -> str:
    """
    Get track purchase history for a customer, showing what music they've bought.
    
    Args:
        customer_id: The customer's ID
    
    Returns:
        Formatted list of purchased tracks with artist and genre
    """
    with get_db() as conn:
        cur = conn.execute("""
            SELECT 
                t.Name as Track, 
                ar.Name as Artist, 
                al.Title as Album,
                g.Name as Genre,
                ii.UnitPrice as Price,
                i.InvoiceDate as PurchaseDate
            FROM invoice_items ii
            JOIN invoices i ON ii.InvoiceId = i.InvoiceId
            JOIN tracks t ON ii.TrackId = t.TrackId
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            LEFT JOIN genres g ON t.GenreId = g.GenreId
            WHERE i.CustomerId = ?
            ORDER BY i.InvoiceDate DESC
        """, (customer_id,))
        rows = cur.fetchall()
    
    if not rows:
        return "You haven't purchased any tracks yet."
    
    lines = []
    for r in rows:
        lines.append(f"• \"{r['Track']}\" by {r['Artist']} ({r['Genre']}) - ${r['Price']:.2f}")
    
    return f"Your purchased tracks ({len(rows)} total):\n" + "\n".join(lines)


@tool
def get_invoice_details(customer_id: int, invoice_id: int) -> str:
    """
    Get detailed line items for a specific invoice.
    
    Args:
        customer_id: The customer's ID (for verification)
        invoice_id: The invoice ID to look up
    
    Returns:
        Detailed invoice with all line items
    """
    with get_db() as conn:
        # Verify invoice belongs to customer
        cur = conn.execute("""
            SELECT i.InvoiceId, i.InvoiceDate, i.Total, 
                   i.BillingAddress, i.BillingCity, i.BillingCountry
            FROM invoices i
            WHERE i.InvoiceId = ? AND i.CustomerId = ?
        """, (invoice_id, customer_id))
        invoice = cur.fetchone()
        
        if not invoice:
            return f"Invoice #{invoice_id} not found or doesn't belong to you."
        
        # Get line items
        cur = conn.execute("""
            SELECT t.Name as Track, ar.Name as Artist, ii.UnitPrice, ii.Quantity
            FROM invoice_items ii
            JOIN tracks t ON ii.TrackId = t.TrackId
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            WHERE ii.InvoiceId = ?
        """, (invoice_id,))
        items = cur.fetchall()
    
    lines = [
        f"Invoice #{invoice['InvoiceId']}",
        f"Date: {invoice['InvoiceDate']}",
        f"Billing: {invoice['BillingAddress']}, {invoice['BillingCity']}, {invoice['BillingCountry']}",
        f"",
        "Items:"
    ]
    
    for item in items:
        lines.append(f"  • \"{item['Track']}\" by {item['Artist']} - ${item['UnitPrice']:.2f} x {item['Quantity']}")
    
    lines.append(f"")
    lines.append(f"Total: ${invoice['Total']:.2f}")
    
    return "\n".join(lines)


# Export list of customer tools
CUSTOMER_TOOLS = [
    get_my_invoices,
    get_my_purchases,
    get_invoice_details,
]
```

### File: `agent/src/tools/employee_tools.py`

```python
"""Tools for employee queries. No auth checks - agent-level auth only."""

from langchain_core.tools import tool
from ..db import get_db


@tool
def get_employee_info(employee_id: int) -> str:
    """
    Get the employee's own information.
    
    Args:
        employee_id: The employee's ID
    
    Returns:
        Employee profile information
    """
    with get_db() as conn:
        cur = conn.execute("""
            SELECT 
                e.FirstName, e.LastName, e.Title, e.Email, e.Phone,
                e.HireDate, e.Address, e.City, e.State, e.Country,
                m.FirstName || ' ' || m.LastName as ManagerName
            FROM employees e
            LEFT JOIN employees m ON e.ReportsTo = m.EmployeeId
            WHERE e.EmployeeId = ?
        """, (employee_id,))
        row = cur.fetchone()
    
    if not row:
        return f"Employee {employee_id} not found."
    
    return f"""Employee Profile:
Name: {row['FirstName']} {row['LastName']}
Title: {row['Title']}
Email: {row['Email']}
Phone: {row['Phone']}
Hire Date: {row['HireDate']}
Location: {row['Address']}, {row['City']}, {row['State']}, {row['Country']}
Reports To: {row['ManagerName'] or 'N/A'}"""


@tool
def get_supported_customers(employee_id: int) -> str:
    """
    Get list of customers this employee supports.
    
    Args:
        employee_id: The employee's ID
    
    Returns:
        List of supported customers with their details
    """
    with get_db() as conn:
        cur = conn.execute("""
            SELECT 
                c.CustomerId, c.FirstName, c.LastName, c.Email, c.City, c.Country,
                COUNT(i.InvoiceId) as InvoiceCount,
                COALESCE(SUM(i.Total), 0) as TotalSpent
            FROM customers c
            LEFT JOIN invoices i ON c.CustomerId = i.CustomerId
            WHERE c.SupportRepId = ?
            GROUP BY c.CustomerId
            ORDER BY c.LastName, c.FirstName
        """, (employee_id,))
        rows = cur.fetchall()
    
    if not rows:
        return "You don't have any assigned customers."
    
    lines = [f"Your supported customers ({len(rows)} total):\n"]
    for r in rows:
        lines.append(
            f"• {r['FirstName']} {r['LastName']} (ID: {r['CustomerId']}) - "
            f"{r['Email']} - {r['City']}, {r['Country']} - "
            f"{r['InvoiceCount']} invoices, ${r['TotalSpent']:.2f} total"
        )
    
    return "\n".join(lines)


@tool
def get_customer_invoices(customer_id: int) -> str:
    """
    Get all invoices for a customer you support.
    
    Args:
        customer_id: The customer's ID
    
    Returns:
        List of invoices for the customer
    """
    with get_db() as conn:
        # Get customer info
        cur = conn.execute("""
            SELECT FirstName, LastName FROM customers WHERE CustomerId = ?
        """, (customer_id,))
        customer = cur.fetchone()
        
        if not customer:
            return f"Customer {customer_id} not found."
        
        # Get invoices
        cur = conn.execute("""
            SELECT InvoiceId, InvoiceDate, BillingCity, BillingCountry, Total
            FROM invoices
            WHERE CustomerId = ?
            ORDER BY InvoiceDate DESC
        """, (customer_id,))
        rows = cur.fetchall()
    
    if not rows:
        return f"{customer['FirstName']} {customer['LastName']} has no invoices."
    
    lines = [f"Invoices for {customer['FirstName']} {customer['LastName']} (ID: {customer_id}):\n"]
    for r in rows:
        lines.append(
            f"  Invoice #{r['InvoiceId']} - {r['InvoiceDate']} - "
            f"${r['Total']:.2f} ({r['BillingCity']}, {r['BillingCountry']})"
        )
    
    return "\n".join(lines)


@tool
def edit_invoice(invoice_id: int, new_total: float) -> str:
    """
    Edit an invoice's total amount. REQUIRES MANAGER APPROVAL.
    
    Args:
        invoice_id: The invoice ID to edit
        new_total: The new total amount
    
    Returns:
        Confirmation of the edit
    """
    with get_db() as conn:
        # Get current invoice info
        cur = conn.execute("""
            SELECT i.Total, c.FirstName, c.LastName
            FROM invoices i
            JOIN customers c ON i.CustomerId = c.CustomerId
            WHERE i.InvoiceId = ?
        """, (invoice_id,))
        row = cur.fetchone()
        
        if not row:
            return f"Invoice #{invoice_id} not found."
        
        old_total = row['Total']
        customer_name = f"{row['FirstName']} {row['LastName']}"
        
        # Perform the update
        conn.execute(
            "UPDATE invoices SET Total = ? WHERE InvoiceId = ?",
            (new_total, invoice_id)
        )
        conn.commit()
    
    return f"✅ Invoice #{invoice_id} for {customer_name} updated: ${old_total:.2f} → ${new_total:.2f}"


@tool
def delete_invoice(invoice_id: int) -> str:
    """
    Delete an invoice. REQUIRES MANAGER APPROVAL.
    
    Args:
        invoice_id: The invoice ID to delete
    
    Returns:
        Confirmation of deletion
    """
    with get_db() as conn:
        # Get invoice info before deletion
        cur = conn.execute("""
            SELECT i.InvoiceId, i.Total, i.InvoiceDate, c.FirstName, c.LastName
            FROM invoices i
            JOIN customers c ON i.CustomerId = c.CustomerId
            WHERE i.InvoiceId = ?
        """, (invoice_id,))
        row = cur.fetchone()
        
        if not row:
            return f"Invoice #{invoice_id} not found."
        
        customer_name = f"{row['FirstName']} {row['LastName']}"
        
        # Delete line items first (foreign key constraint)
        conn.execute("DELETE FROM invoice_items WHERE InvoiceId = ?", (invoice_id,))
        # Delete invoice
        conn.execute("DELETE FROM invoices WHERE InvoiceId = ?", (invoice_id,))
        conn.commit()
    
    return f"✅ Invoice #{invoice_id} for {customer_name} (${row['Total']:.2f}, {row['InvoiceDate']}) has been deleted."


# Tools that require human-in-the-loop approval
HITL_TOOLS = {"edit_invoice", "delete_invoice"}

# Export list of employee tools
EMPLOYEE_TOOLS = [
    get_employee_info,
    get_supported_customers,
    get_customer_invoices,
    edit_invoice,
    delete_invoice,
]
```

### File: `agent/src/tools/recommendation_tools.py`

```python
"""Tools for music recommendations based on purchase history."""

from langchain_core.tools import tool
from ..db import get_db


@tool
def get_genre_recommendations(customer_id: int) -> str:
    """
    Get music recommendations based on customer's purchase history.
    Analyzes genres they've bought and suggests similar tracks they haven't purchased.
    
    Args:
        customer_id: The customer's ID
    
    Returns:
        Personalized track recommendations based on genre preferences
    """
    with get_db() as conn:
        # Find genres the customer has purchased from
        cur = conn.execute("""
            SELECT g.GenreId, g.Name, COUNT(*) as PurchaseCount
            FROM invoice_items ii
            JOIN invoices i ON ii.InvoiceId = i.InvoiceId
            JOIN tracks t ON ii.TrackId = t.TrackId
            JOIN genres g ON t.GenreId = g.GenreId
            WHERE i.CustomerId = ?
            GROUP BY g.GenreId
            ORDER BY PurchaseCount DESC
            LIMIT 3
        """, (customer_id,))
        top_genres = cur.fetchall()
        
        if not top_genres:
            return "No purchase history found. Browse our catalog to get started!"
        
        # Get tracks they haven't purchased from their top genres
        genre_ids = [g['GenreId'] for g in top_genres]
        placeholders = ','.join('?' * len(genre_ids))
        
        cur = conn.execute(f"""
            SELECT DISTINCT t.TrackId, t.Name as Track, ar.Name as Artist, 
                   g.Name as Genre, t.UnitPrice
            FROM tracks t
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            JOIN genres g ON t.GenreId = g.GenreId
            WHERE t.GenreId IN ({placeholders})
            AND t.TrackId NOT IN (
                SELECT ii.TrackId 
                FROM invoice_items ii
                JOIN invoices i ON ii.InvoiceId = i.InvoiceId
                WHERE i.CustomerId = ?
            )
            ORDER BY RANDOM()
            LIMIT 10
        """, (*genre_ids, customer_id))
        recommendations = cur.fetchall()
    
    # Build response
    genre_summary = ", ".join([f"{g['Name']} ({g['PurchaseCount']} tracks)" for g in top_genres])
    
    lines = [
        f"Based on your favorite genres ({genre_summary}), you might like:\n"
    ]
    
    for r in recommendations:
        lines.append(f"• \"{r['Track']}\" by {r['Artist']} ({r['Genre']}) - ${r['UnitPrice']:.2f}")
    
    return "\n".join(lines)


@tool
def get_artist_recommendations(customer_id: int) -> str:
    """
    Recommend artists similar to ones the customer has purchased.
    Finds artists in the same genres as their favorite artists.
    
    Args:
        customer_id: The customer's ID
    
    Returns:
        List of recommended artists they haven't purchased from
    """
    with get_db() as conn:
        # Find genres from artists they've purchased
        cur = conn.execute("""
            SELECT DISTINCT g.GenreId
            FROM invoice_items ii
            JOIN invoices i ON ii.InvoiceId = i.InvoiceId
            JOIN tracks t ON ii.TrackId = t.TrackId
            JOIN genres g ON t.GenreId = g.GenreId
            WHERE i.CustomerId = ?
        """, (customer_id,))
        genre_ids = [r['GenreId'] for r in cur.fetchall()]
        
        if not genre_ids:
            return "No purchase history found. Check out our popular artists!"
        
        # Find artists in those genres they haven't bought from
        placeholders = ','.join('?' * len(genre_ids))
        cur = conn.execute(f"""
            SELECT DISTINCT ar.ArtistId, ar.Name as Artist, 
                   COUNT(DISTINCT t.TrackId) as TrackCount,
                   GROUP_CONCAT(DISTINCT g.Name) as Genres
            FROM artists ar
            JOIN albums al ON ar.ArtistId = al.ArtistId
            JOIN tracks t ON al.AlbumId = t.AlbumId
            JOIN genres g ON t.GenreId = g.GenreId
            WHERE g.GenreId IN ({placeholders})
            AND ar.ArtistId NOT IN (
                SELECT DISTINCT ar2.ArtistId
                FROM invoice_items ii
                JOIN invoices inv ON ii.InvoiceId = inv.InvoiceId
                JOIN tracks t2 ON ii.TrackId = t2.TrackId
                JOIN albums al2 ON t2.AlbumId = al2.AlbumId
                JOIN artists ar2 ON al2.ArtistId = ar2.ArtistId
                WHERE inv.CustomerId = ?
            )
            GROUP BY ar.ArtistId
            ORDER BY TrackCount DESC
            LIMIT 10
        """, (*genre_ids, customer_id))
        artists = cur.fetchall()
    
    if not artists:
        return "Wow, you've explored a lot! Check back later for new artists."
    
    lines = ["Artists you might enjoy:\n"]
    for a in artists:
        lines.append(f"• {a['Artist']} - {a['TrackCount']} tracks ({a['Genres']})")
    
    return "\n".join(lines)


@tool  
def get_popular_tracks_in_genre(genre_name: str) -> str:
    """
    Get the most popular (best-selling) tracks in a specific genre.
    
    Args:
        genre_name: Name of the genre (e.g., "Rock", "Jazz", "Metal")
    
    Returns:
        Top 10 best-selling tracks in that genre
    """
    with get_db() as conn:
        cur = conn.execute("""
            SELECT 
                t.Name as Track, 
                ar.Name as Artist,
                al.Title as Album,
                t.UnitPrice,
                COUNT(ii.InvoiceLineId) as TimesSold
            FROM tracks t
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            JOIN genres g ON t.GenreId = g.GenreId
            LEFT JOIN invoice_items ii ON t.TrackId = ii.TrackId
            WHERE LOWER(g.Name) LIKE LOWER(?)
            GROUP BY t.TrackId
            ORDER BY TimesSold DESC, t.Name
            LIMIT 10
        """, (f"%{genre_name}%",))
        rows = cur.fetchall()
    
    if not rows:
        return f"No tracks found in genre matching '{genre_name}'. Try: Rock, Jazz, Metal, Pop, Blues, etc."
    
    lines = [f"Top tracks in {genre_name}:\n"]
    for r in rows:
        sold_text = f"({r['TimesSold']} sold)" if r['TimesSold'] > 0 else "(new)"
        lines.append(f"• \"{r['Track']}\" by {r['Artist']} - ${r['UnitPrice']:.2f} {sold_text}")
    
    return "\n".join(lines)


# Export list of recommendation tools
RECOMMENDATION_TOOLS = [
    get_genre_recommendations,
    get_artist_recommendations,
    get_popular_tracks_in_genre,
]
```

### File: `agent/src/nodes/__init__.py`

```python
"""Agent nodes package."""

from .supervisor import supervisor_node
from .customer_agent import customer_agent_node
from .employee_agent import employee_agent_node
from .recommendation_agent import recommendation_agent_node

__all__ = [
    "supervisor_node",
    "customer_agent_node", 
    "employee_agent_node",
    "recommendation_agent_node",
]
```

### File: `agent/src/nodes/supervisor.py`

```python
"""Supervisor node that routes to appropriate agent based on user role and intent."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from ..state import AgentState

model = ChatAnthropic(model="claude-sonnet-4-20250514")

ROUTING_PROMPT = """You are a supervisor routing requests for a music store assistant system.

User Information:
- Name: {user_name}
- Role: {role}
- {role_context}

Based on the user's message, decide which agent should handle this request:

AGENTS:
- "customer_agent": For viewing personal invoices, purchase history, account information
- "employee_agent": For employee info, viewing/managing supported customers, editing invoices
- "recommendation_agent": For music recommendations, discovering new artists, genre exploration
- "FINISH": If the conversation is complete or the query has been fully answered

RULES:
- Customers can ONLY use: customer_agent, recommendation_agent
- Employees can ONLY use: employee_agent, recommendation_agent
- For greetings or simple questions, respond directly and output FINISH

Respond with ONLY the agent name (customer_agent, employee_agent, recommendation_agent, or FINISH)."""


async def supervisor_node(state: AgentState, config: dict) -> Command:
    """Route to appropriate agent based on user role and intent."""
    
    # Get auth context
    auth_user = config.get("configurable", {}).get("langgraph_auth_user", {})
    role = auth_user.get("role", "customer")
    user_name = auth_user.get("name", "User")
    
    # Build role-specific context
    if role == "employee":
        supported = auth_user.get("supported_customers", [])
        role_context = f"Supported Customer IDs: {supported}"
        valid_agents = ["employee_agent", "recommendation_agent", "FINISH"]
    else:
        role_context = f"Customer ID: {auth_user.get('customer_id', 'unknown')}"
        valid_agents = ["customer_agent", "recommendation_agent", "FINISH"]
    
    # Get the last user message
    last_message = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "type") and msg.type == "human":
            last_message = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            last_message = msg.get("content", "")
            break
    
    # Ask LLM to route
    response = await model.ainvoke([
        SystemMessage(content=ROUTING_PROMPT.format(
            user_name=user_name,
            role=role,
            role_context=role_context
        )),
        HumanMessage(content=f"User message: {last_message}")
    ])
    
    next_agent = response.content.strip().lower()
    
    # Validate and enforce role restrictions
    if next_agent not in [a.lower() for a in valid_agents]:
        # Default to the primary agent for the role
        next_agent = "customer_agent" if role == "customer" else "employee_agent"
    
    if next_agent == "finish":
        return Command(goto="__end__")
    
    return Command(goto=next_agent)
```

### File: `agent/src/nodes/customer_agent.py`

```python
"""Customer agent node - handles customer queries about their own account."""

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from ..state import AgentState
from ..tools.customer_tools import CUSTOMER_TOOLS

model = ChatAnthropic(model="claude-sonnet-4-20250514")


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


async def customer_agent_node(state: AgentState, config: dict) -> Command:
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
```

### File: `agent/src/nodes/employee_agent.py`

```python
"""Employee agent node - handles employee queries with HITL for invoice mutations."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from ..state import AgentState
from ..tools.employee_tools import EMPLOYEE_TOOLS, HITL_TOOLS

model = ChatAnthropic(model="claude-sonnet-4-20250514")


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


async def employee_agent_node(state: AgentState, config: dict) -> Command:
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
                    "message": f"🔐 Manager Approval Required\n\nAction: {tool_call['name']}\nInvoice ID: {tool_call['args'].get('invoice_id')}\n\nDo you approve this action?"
                }
                
                # This will pause execution and wait for human input
                approval = interrupt(approval_request)
                
                if not approval or not approval.get("approved", False):
                    # Action was rejected
                    return Command(
                        goto="supervisor",
                        update={
                            "messages": [
                                AIMessage(content="❌ The action was not approved by the manager. No changes were made.")
                            ]
                        }
                    )
                
                # Action was approved - the tool already executed in the agent
                # Add confirmation message
                return Command(
                    goto="supervisor", 
                    update={
                        "messages": result["messages"] + [
                            AIMessage(content="✅ Manager approval received. Action completed successfully.")
                        ]
                    }
                )
    
    return Command(
        goto="supervisor",
        update={"messages": result["messages"]}
    )
```

### File: `agent/src/nodes/recommendation_agent.py`

```python
"""Recommendation agent node - handles music recommendations for all users."""

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from ..state import AgentState
from ..tools.recommendation_tools import RECOMMENDATION_TOOLS

model = ChatAnthropic(model="claude-sonnet-4-20250514")


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


async def recommendation_agent_node(state: AgentState, config: dict) -> Command:
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
```

### File: `agent/src/agent.py`

```python
"""Main graph composition for the music store multi-agent system."""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes import (
    supervisor_node,
    customer_agent_node,
    employee_agent_node,
    recommendation_agent_node,
)


def create_graph():
    """Create and compile the multi-agent graph."""
    
    builder = StateGraph(AgentState)
    
    # Add all nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("customer_agent", customer_agent_node)
    builder.add_node("employee_agent", employee_agent_node)
    builder.add_node("recommendation_agent", recommendation_agent_node)
    
    # Entry point - always start with supervisor
    builder.add_edge(START, "supervisor")
    
    # Supervisor can route to any agent or end
    # (routing is handled by Command in supervisor_node)
    
    # All agents route back to supervisor after completing
    # (routing is handled by Command in each agent node)
    
    # Compile with checkpointer for conversation persistence
    checkpointer = MemorySaver()
    
    return builder.compile(checkpointer=checkpointer)


# Export the compiled graph
graph = create_graph()
```

---

## Frontend Implementation

### File: `frontend/package.json`

```json
{
  "name": "music-store-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@copilotkit/react-core": "^1.0.0",
    "@copilotkit/react-ui": "^1.0.0",
    "@copilotkit/runtime": "^1.0.0",
    "next": "14.2.0",
    "react": "^18",
    "react-dom": "^18"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "typescript": "^5",
    "tailwindcss": "^3.4.0",
    "postcss": "^8",
    "autoprefixer": "^10"
  }
}
```

### File: `frontend/.env.local`

```bash
# For local development with langgraph dev
LANGGRAPH_DEPLOYMENT_URL=http://localhost:8123

# For production (update after deploying to LangGraph Platform)
# LANGGRAPH_DEPLOYMENT_URL=https://your-deployment.langsmith.com

LANGCHAIN_API_KEY=your-langsmith-api-key
```

### File: `frontend/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Music Store Assistant",
  description: "Multi-agent music store demo with LangGraph",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

### File: `frontend/app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground: #171717;
  --background: #ffffff;
}

body {
  color: var(--foreground);
  background: var(--background);
  font-family: Arial, Helvetica, sans-serif;
}

/* Custom styles for the chat interface */
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.user-selector {
  padding: 1rem;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.user-selector select {
  padding: 0.5rem 1rem;
  font-size: 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
}

/* Approval dialog styles */
.approval-dialog {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  padding: 1rem;
  margin: 1rem 0;
}

.approval-dialog h3 {
  margin: 0 0 0.5rem 0;
  color: #856404;
}

.approval-dialog .buttons {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}

.approval-dialog button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.approval-dialog button:first-child {
  background: #28a745;
  color: white;
}

.approval-dialog button:last-child {
  background: #dc3545;
  color: white;
}
```

### File: `frontend/app/api/copilotkit/route.ts`

```typescript
import { CopilotRuntime, LangGraphAgent } from "@copilotkit/runtime";
import { NextRequest } from "next/server";

export const runtime = "edge";

export async function POST(req: NextRequest) {
  const copilotRuntime = new CopilotRuntime({
    agents: {
      music_store: new LangGraphAgent({
        deploymentUrl: process.env.LANGGRAPH_DEPLOYMENT_URL!,
        graphId: "music_store",
        langsmithApiKey: process.env.LANGCHAIN_API_KEY,
      }),
    },
  });

  return copilotRuntime.handleRequest(req);
}
```

### File: `frontend/app/page.tsx`

```tsx
"use client";

import { useState } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useLangGraphInterrupt } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

// Demo users matching the database
const DEMO_USERS = [
  { 
    id: "julia", 
    name: "Julia Schottenstein", 
    role: "employee",
    description: "Sales Support Agent - Supports Jake & Neil"
  },
  { 
    id: "jake", 
    name: "Jake Broekhuizen", 
    role: "customer",
    description: "Customer - 4 invoices"
  },
  { 
    id: "neil", 
    name: "Neil Dahlke", 
    role: "customer",
    description: "Customer - 4 invoices"
  },
];

// Component to handle HITL interrupts for manager approval
function ApprovalHandler() {
  useLangGraphInterrupt<{ 
    type: string; 
    action: string; 
    args: Record<string, unknown>;
    message: string;
  }>({
    render: ({ event, resolve }) => {
      if (event.value.type !== "manager_approval") {
        return null;
      }
      
      return (
        <div className="approval-dialog">
          <h3>🔐 Manager Approval Required</h3>
          <p style={{ whiteSpace: "pre-line" }}>{event.value.message}</p>
          <div className="buttons">
            <button onClick={() => resolve({ approved: true })}>
              ✅ Approve
            </button>
            <button onClick={() => resolve({ approved: false })}>
              ❌ Reject
            </button>
          </div>
        </div>
      );
    },
  });
  
  return null;
}

export default function Home() {
  const [currentUser, setCurrentUser] = useState(DEMO_USERS[0]);
  // Key to force remount of CopilotKit when user changes
  const [chatKey, setChatKey] = useState(0);

  const handleUserChange = (userId: string) => {
    const user = DEMO_USERS.find(u => u.id === userId);
    if (user) {
      setCurrentUser(user);
      // Increment key to reset the chat
      setChatKey(prev => prev + 1);
    }
  };

  return (
    <CopilotKit
      key={chatKey}
      runtimeUrl="/api/copilotkit"
      agent="music_store"
      properties={{
        authorization: `Bearer ${currentUser.id}`,
      }}
    >
      <div className="chat-container">
        {/* Header with user selector */}
        <header className="user-selector">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h1 style={{ margin: 0, fontSize: "1.5rem" }}>🎵 Music Store Assistant</h1>
              <p style={{ margin: "0.25rem 0 0 0", color: "#666", fontSize: "0.9rem" }}>
                LangGraph Multi-Agent Demo
              </p>
            </div>
            <div style={{ textAlign: "right" }}>
              <label style={{ display: "block", marginBottom: "0.25rem", fontSize: "0.8rem", color: "#666" }}>
                Switch User:
              </label>
              <select 
                value={currentUser.id}
                onChange={(e) => handleUserChange(e.target.value)}
              >
                {DEMO_USERS.map(user => (
                  <option key={user.id} value={user.id}>
                    {user.name} ({user.role})
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ 
            marginTop: "0.5rem", 
            padding: "0.5rem", 
            background: currentUser.role === "employee" ? "#e3f2fd" : "#e8f5e9",
            borderRadius: "4px",
            fontSize: "0.85rem"
          }}>
            <strong>Logged in as:</strong> {currentUser.name} ({currentUser.role})
            <br />
            <span style={{ color: "#666" }}>{currentUser.description}</span>
          </div>
        </header>
        
        {/* HITL Approval Handler */}
        <ApprovalHandler />
        
        {/* Chat Interface */}
        <div style={{ flex: 1, overflow: "hidden" }}>
          <CopilotChat
            labels={{
              title: `Hello, ${currentUser.name.split(' ')[0]}!`,
              initial: currentUser.role === "employee"
                ? "Hi! I can help you with your employee info, manage your supported customers (Jake & Neil), or explore music recommendations. What would you like to do?"
                : "Hi! I can help you view your invoices, see your purchase history, or get personalized music recommendations. How can I help?",
            }}
          />
        </div>
      </div>
    </CopilotKit>
  );
}
```

### File: `frontend/next.config.js`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable edge runtime for API routes
  experimental: {
    serverActions: true,
  },
};

module.exports = nextConfig;
```

### File: `frontend/tailwind.config.js`

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

### File: `frontend/postcss.config.js`

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

### File: `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

## Running the Demo

### Local Development

**Terminal 1 - Backend:**
```bash
cd agent

# Copy the chinook.db file to agent directory
cp /path/to/chinook.db .

# Install dependencies
pip install -e .

# Run LangGraph dev server
langgraph dev --port 8123
```

**Terminal 2 - Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Run Next.js dev server
npm run dev
```

**Access:** Open http://localhost:3000

### Production Deployment

**Backend (LangGraph Platform):**

1. Push `agent/` directory to a GitHub repository
2. Go to LangSmith → Deployments → New Deployment
3. Connect your GitHub repo
4. Set environment variables:
   - `ANTHROPIC_API_KEY`
5. Deploy and note the deployment URL

**Frontend (Vercel):**

1. Push `frontend/` directory to GitHub
2. Import to Vercel
3. Set environment variables:
   - `LANGGRAPH_DEPLOYMENT_URL` = your LangGraph deployment URL
   - `LANGCHAIN_API_KEY` = your LangSmith API key
4. Deploy

---

## Test Scenarios

### Customer Tests (as Jake or Neil)

| Query | Expected Behavior |
|-------|-------------------|
| "Show me my invoices" | Returns invoices 413-416 (Jake) or 417-420 (Neil) |
| "What music have I bought?" | Shows purchased tracks with artist/genre |
| "Give me details on invoice 413" | Shows line items for that invoice |
| "Recommend me some new music" | Analyzes purchase history, suggests similar tracks |
| "What's popular in Rock?" | Shows top-selling Rock tracks |

### Employee Tests (as Julia)

| Query | Expected Behavior |
|-------|-------------------|
| "Show me my employee info" | Returns Julia's profile |
| "Which customers do I support?" | Lists Jake and Neil with stats |
| "Show me Jake's invoices" | Returns Jake's 4 invoices |
| "Show me Neil's invoices" | Returns Neil's 4 invoices |
| "Edit invoice 413, change total to 10.00" | Triggers HITL approval dialog |
| "Delete invoice 417" | Triggers HITL approval dialog |

### Authorization Tests

| Query | User | Expected Behavior |
|-------|------|-------------------|
| "Show me customer 60's invoices" | Jake (customer) | Routes to customer_agent, cannot access |
| "Edit invoice 413" | Jake (customer) | Tool not available to customer agent |
| "Show me employee info" | Jake (customer) | Routes to customer_agent, tool not available |

---

## LangSmith Tracing

Traces automatically appear in LangSmith when `LANGCHAIN_TRACING_V2=true`:

- View at: https://smith.langchain.com
- Project: `music-store-demo` (or as configured)
- Each conversation creates a trace showing:
  - Auth handler execution
  - Supervisor routing decisions
  - Agent tool calls
  - HITL interrupts and resolutions

---

## Key Implementation Notes

| Feature | Implementation |
|---------|----------------|
| **LangSmith Tracing** | Automatic via `LANGCHAIN_TRACING_V2=true` |
| **Auth** | Custom handler in `auth.py`, referenced in `langgraph.json` |
| **Role-based Routing** | Supervisor checks `role` from auth context |
| **Agent-level Auth** | Each agent only has tools appropriate for its role |
| **Tool User Context** | Agent prompt injects user IDs for tools |
| **HITL** | `interrupt()` in employee_agent for edit/delete |
| **Frontend HITL** | `useLangGraphInterrupt()` renders approval UI |
| **CopilotKit Auth** | `properties.authorization` passed to backend |
