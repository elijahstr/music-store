"""Tools for employee queries. No auth checks - agent-level auth only."""

from langchain_core.tools import tool
from langgraph.types import interrupt
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

    # Request manager approval BEFORE making changes
    approval = interrupt({
        "type": "manager_approval",
        "action": "edit_invoice",
        "invoice_id": invoice_id,
        "customer_name": customer_name,
        "old_total": float(old_total),
        "new_total": new_total,
        "message": f"Approve editing Invoice #{invoice_id} for {customer_name}?\nChange: ${old_total:.2f} -> ${new_total:.2f}"
    })

    if not approval or not approval.get("approved", False):
        return f"Edit of Invoice #{invoice_id} was not approved. No changes made."

    # Approved - now perform the update
    with get_db() as conn:
        conn.execute(
            "UPDATE invoices SET Total = ? WHERE InvoiceId = ?",
            (new_total, invoice_id)
        )
        conn.commit()

    return f"Invoice #{invoice_id} for {customer_name} updated: ${old_total:.2f} -> ${new_total:.2f}"


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
        total = row['Total']
        invoice_date = row['InvoiceDate']

    # Request manager approval BEFORE deleting
    approval = interrupt({
        "type": "manager_approval",
        "action": "delete_invoice",
        "invoice_id": invoice_id,
        "customer_name": customer_name,
        "total": float(total),
        "invoice_date": str(invoice_date),
        "message": f"Approve deleting Invoice #{invoice_id} for {customer_name}?\nAmount: ${total:.2f}, Date: {invoice_date}"
    })

    if not approval or not approval.get("approved", False):
        return f"Deletion of Invoice #{invoice_id} was not approved. No changes made."

    # Approved - now perform the deletion
    with get_db() as conn:
        # Delete line items first (foreign key constraint)
        conn.execute("DELETE FROM invoice_items WHERE InvoiceId = ?", (invoice_id,))
        # Delete invoice
        conn.execute("DELETE FROM invoices WHERE InvoiceId = ?", (invoice_id,))
        conn.commit()

    return f"Invoice #{invoice_id} for {customer_name} (${total:.2f}, {invoice_date}) has been deleted."


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
