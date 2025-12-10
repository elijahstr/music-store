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
        "",
        "Items:"
    ]

    for item in items:
        lines.append(f"  • \"{item['Track']}\" by {item['Artist']} - ${item['UnitPrice']:.2f} x {item['Quantity']}")

    lines.append("")
    lines.append(f"Total: ${invoice['Total']:.2f}")

    return "\n".join(lines)


# Export list of customer tools
CUSTOMER_TOOLS = [
    get_my_invoices,
    get_my_purchases,
    get_invoice_details,
]
