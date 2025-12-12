"""Utility functions for the music store agent."""

import asyncio
from langchain_core.runnables import RunnableConfig
from .db import get_db


def _lookup_user_sync(token: str) -> dict | None:
    """Synchronous database lookup for user authentication."""
    with get_db() as conn:
        # Check if token matches an employee
        cur = conn.execute("""
            SELECT EmployeeId, FirstName, LastName
            FROM employees
            WHERE LOWER(FirstName) = ?
        """, (token.lower(),))
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
        """, (token.lower(),))
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

    return None


async def get_auth_user(config: RunnableConfig) -> dict:
    """
    Get authenticated user from config, checking multiple sources.

    Priority:
    1. langgraph_auth_user (from auth handler)
    2. authorization in context (LangGraph 0.6.0+)
    3. authorization in configurable (legacy)
    4. Default studio user (fallback for dev)
    """
    configurable = config.get("configurable", {})
    # LangGraph 0.6.0+ uses context instead of configurable
    context = config.get("context", {})

    # Source 1: Auth handler result
    auth_user = configurable.get("langgraph_auth_user", {})

    # Check if we got a real user (not the studio fallback)
    if auth_user.get("identity") and auth_user.get("identity") != "studio":
        print(f"[AUTH UTIL] Using langgraph_auth_user: {auth_user.get('name')} ({auth_user.get('role')})")
        return auth_user

    # Source 2: Authorization from context (LangGraph 0.6.0+)
    auth_header = context.get("authorization")
    if auth_header:
        token = auth_header.replace("Bearer ", "").strip()
        print(f"[AUTH UTIL] Looking up user from context.authorization: {token}")
        user_data = await asyncio.to_thread(_lookup_user_sync, token)
        if user_data:
            print(f"[AUTH UTIL] Found user: {user_data.get('name')} ({user_data.get('role')})")
            return user_data

    # Source 3: Authorization header from configurable_headers (legacy)
    auth_header = configurable.get("authorization")
    if auth_header:
        token = auth_header.replace("Bearer ", "").strip()
        print(f"[AUTH UTIL] Looking up user from configurable.authorization: {token}")
        user_data = await asyncio.to_thread(_lookup_user_sync, token)
        if user_data:
            print(f"[AUTH UTIL] Found user: {user_data.get('name')} ({user_data.get('role')})")
            return user_data

    # Fallback: Return the auth_user (which may be the studio default)
    print(f"[AUTH UTIL] Using fallback auth_user: {auth_user.get('name', 'Unknown')} ({auth_user.get('role', 'unknown')})")
    return auth_user
