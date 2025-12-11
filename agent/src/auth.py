"""Custom authentication handler for LangGraph Platform."""

import asyncio
from langgraph_sdk import Auth
from langgraph_sdk.auth import is_studio_user
from .db import get_db

auth = Auth()


def _lookup_user(token: str) -> dict | None:
    """Synchronous database lookup for user authentication."""
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

    return None


@auth.authenticate
async def authenticate(authorization: str | None) -> Auth.types.MinimalUserDict:
    """
    Validate user token and return identity + context.

    For this demo, token is the user's first name (julia, jake, neil).
    In production, this would validate a real JWT/session token.
    """
    # Allow Studio access in dev mode (no authorization provided)
    if not authorization:
        # Return a default employee user for Studio/dev access
        return {
            "identity": "studio",
            "role": "employee",
            "employee_id": 9,  # Julia's ID for demo purposes
            "user_id": 9,
            "name": "Studio User",
            "supported_customers": [60, 61],  # Jake and Neil
            "permissions": ["employee:read", "employee:write", "customer:read"],
        }

    # Extract token from "Bearer <token>" format
    token = authorization.replace("Bearer ", "").strip().lower()

    # Run blocking database call in thread pool
    user_data = await asyncio.to_thread(_lookup_user, token)

    if user_data:
        return user_data

    # No matching user found
    raise Auth.exceptions.HTTPException(
        status_code=401,
        detail=f"Unknown user: {token}"
    )


@auth.on
async def add_owner_metadata(ctx: Auth.types.AuthContext, value: dict):
    """Add owner metadata to resources for filtering."""
    # Allow Studio users full access without filters
    if is_studio_user(ctx.user):
        return {}

    metadata = value.setdefault("metadata", {})
    # Handle both dict (custom auth) and StudioUser (studio mode) types
    if hasattr(ctx.user, "identity"):
        identity = ctx.user.identity
    elif isinstance(ctx.user, dict):
        identity = ctx.user.get("identity", "unknown")
    else:
        identity = "studio"
    metadata["owner"] = identity
    return {"owner": identity}
