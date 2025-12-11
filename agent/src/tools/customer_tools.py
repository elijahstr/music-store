"""Tools for customer queries. No auth checks - agent-level auth only."""

from datetime import datetime
from langchain_core.tools import tool
from langgraph.types import interrupt
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


@tool
def search_tracks(query: str) -> str:
    """
    Search for tracks by name, artist, or album.

    Args:
        query: Search term to find tracks

    Returns:
        List of matching tracks with TrackId, name, artist, album, and price
    """
    with get_db() as conn:
        search_term = f"%{query}%"
        cur = conn.execute("""
            SELECT t.TrackId, t.Name as Track, ar.Name as Artist,
                   al.Title as Album, g.Name as Genre, t.UnitPrice
            FROM tracks t
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            LEFT JOIN genres g ON t.GenreId = g.GenreId
            WHERE t.Name LIKE ? OR ar.Name LIKE ? OR al.Title LIKE ?
            ORDER BY ar.Name, al.Title, t.Name
            LIMIT 20
        """, (search_term, search_term, search_term))
        rows = cur.fetchall()

    if not rows:
        return f"No tracks found matching '{query}'."

    lines = [f"Found {len(rows)} tracks matching '{query}':\n"]
    for r in rows:
        lines.append(
            f"• TrackId {r['TrackId']}: \"{r['Track']}\" by {r['Artist']} "
            f"({r['Album']}) - ${r['UnitPrice']:.2f}"
        )

    return "\n".join(lines)


@tool
def purchase_track(customer_id: int, track_id: int) -> str:
    """
    Purchase a track. REQUIRES CUSTOMER CONFIRMATION before charging.

    Args:
        customer_id: The customer's ID
        track_id: The TrackId of the track to purchase

    Returns:
        Confirmation of purchase or error message
    """
    with get_db() as conn:
        # Get track info
        cur = conn.execute("""
            SELECT t.TrackId, t.Name as Track, t.UnitPrice,
                   ar.Name as Artist, al.Title as Album
            FROM tracks t
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            WHERE t.TrackId = ?
        """, (track_id,))
        track = cur.fetchone()

        if not track:
            return f"Track ID {track_id} not found."

        # Get customer billing info
        cur = conn.execute("""
            SELECT FirstName, LastName, Address, City, State, Country, PostalCode
            FROM customers WHERE CustomerId = ?
        """, (customer_id,))
        customer = cur.fetchone()

        if not customer:
            return f"Customer ID {customer_id} not found."

    # Request purchase confirmation BEFORE charging
    confirmation = interrupt({
        "type": "purchase_confirmation",
        "action": "purchase_track",
        "track_id": track_id,
        "track_name": track['Track'],
        "artist": track['Artist'],
        "album": track['Album'],
        "price": float(track['UnitPrice']),
        "message": f"Confirm purchase of \"{track['Track']}\" by {track['Artist']} for ${track['UnitPrice']:.2f}?"
    })

    if not confirmation or not confirmation.get("confirmed", False):
        return f"Purchase of \"{track['Track']}\" was cancelled. No charge made."

    # Confirmed - create invoice and invoice_item
    with get_db() as conn:
        # Create invoice
        cur = conn.execute("""
            INSERT INTO invoices (CustomerId, InvoiceDate, BillingAddress,
                                  BillingCity, BillingState, BillingCountry,
                                  BillingPostalCode, Total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            customer['Address'],
            customer['City'],
            customer['State'],
            customer['Country'],
            customer['PostalCode'],
            track['UnitPrice']
        ))
        invoice_id = cur.lastrowid

        # Create invoice item
        conn.execute("""
            INSERT INTO invoice_items (InvoiceId, TrackId, UnitPrice, Quantity)
            VALUES (?, ?, ?, 1)
        """, (invoice_id, track_id, track['UnitPrice']))

        conn.commit()

    return (
        f"Purchase complete! Invoice #{invoice_id}\n"
        f"Track: \"{track['Track']}\" by {track['Artist']}\n"
        f"Album: {track['Album']}\n"
        f"Total: ${track['UnitPrice']:.2f}\n"
        f"Thank you for your purchase!"
    )


@tool
def search_albums(query: str) -> str:
    """
    Search for albums by title or artist name.

    Args:
        query: Search term to find albums

    Returns:
        List of matching albums with AlbumId, title, artist, track count, and total price
    """
    with get_db() as conn:
        search_term = f"%{query}%"
        cur = conn.execute("""
            SELECT al.AlbumId, al.Title as Album, ar.Name as Artist,
                   COUNT(t.TrackId) as TrackCount,
                   SUM(t.UnitPrice) as TotalPrice
            FROM albums al
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            JOIN tracks t ON t.AlbumId = al.AlbumId
            WHERE al.Title LIKE ? OR ar.Name LIKE ?
            GROUP BY al.AlbumId
            ORDER BY ar.Name, al.Title
            LIMIT 15
        """, (search_term, search_term))
        rows = cur.fetchall()

    if not rows:
        return f"No albums found matching '{query}'."

    lines = [f"Found {len(rows)} albums matching '{query}':\n"]
    for r in rows:
        lines.append(
            f"• AlbumId {r['AlbumId']}: \"{r['Album']}\" by {r['Artist']} "
            f"({r['TrackCount']} tracks) - ${r['TotalPrice']:.2f} total"
        )

    return "\n".join(lines)


@tool
def purchase_album(customer_id: int, album_id: int) -> str:
    """
    Purchase all tracks from an album. REQUIRES CUSTOMER CONFIRMATION before charging.

    Args:
        customer_id: The customer's ID
        album_id: The AlbumId of the album to purchase

    Returns:
        Confirmation of purchase or error message
    """
    with get_db() as conn:
        # Get album info with all tracks
        cur = conn.execute("""
            SELECT al.AlbumId, al.Title as Album, ar.Name as Artist
            FROM albums al
            JOIN artists ar ON al.ArtistId = ar.ArtistId
            WHERE al.AlbumId = ?
        """, (album_id,))
        album = cur.fetchone()

        if not album:
            return f"Album ID {album_id} not found."

        # Get all tracks in the album
        cur = conn.execute("""
            SELECT TrackId, Name, UnitPrice
            FROM tracks WHERE AlbumId = ?
            ORDER BY TrackId
        """, (album_id,))
        tracks = cur.fetchall()

        if not tracks:
            return f"Album \"{album['Album']}\" has no tracks."

        total_price = sum(t['UnitPrice'] for t in tracks)

        # Get customer billing info
        cur = conn.execute("""
            SELECT FirstName, LastName, Address, City, State, Country, PostalCode
            FROM customers WHERE CustomerId = ?
        """, (customer_id,))
        customer = cur.fetchone()

        if not customer:
            return f"Customer ID {customer_id} not found."

    # Request purchase confirmation BEFORE charging
    confirmation = interrupt({
        "type": "purchase_confirmation",
        "action": "purchase_album",
        "album_id": album_id,
        "album_title": album['Album'],
        "artist": album['Artist'],
        "track_count": len(tracks),
        "price": float(total_price),
        "message": f"Confirm purchase of \"{album['Album']}\" by {album['Artist']} ({len(tracks)} tracks) for ${total_price:.2f}?"
    })

    if not confirmation or not confirmation.get("confirmed", False):
        return f"Purchase of \"{album['Album']}\" was cancelled. No charge made."

    # Confirmed - create invoice and invoice_items for all tracks
    with get_db() as conn:
        # Create invoice
        cur = conn.execute("""
            INSERT INTO invoices (CustomerId, InvoiceDate, BillingAddress,
                                  BillingCity, BillingState, BillingCountry,
                                  BillingPostalCode, Total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            customer['Address'],
            customer['City'],
            customer['State'],
            customer['Country'],
            customer['PostalCode'],
            total_price
        ))
        invoice_id = cur.lastrowid

        # Create invoice items for each track
        for track in tracks:
            conn.execute("""
                INSERT INTO invoice_items (InvoiceId, TrackId, UnitPrice, Quantity)
                VALUES (?, ?, ?, 1)
            """, (invoice_id, track['TrackId'], track['UnitPrice']))

        conn.commit()

    return (
        f"Purchase complete! Invoice #{invoice_id}\n"
        f"Album: \"{album['Album']}\" by {album['Artist']}\n"
        f"Tracks: {len(tracks)}\n"
        f"Total: ${total_price:.2f}\n"
        f"Thank you for your purchase!"
    )


# Export list of customer tools
CUSTOMER_TOOLS = [
    get_my_invoices,
    get_my_purchases,
    get_invoice_details,
    search_tracks,
    search_albums,
    purchase_track,
    purchase_album,
]
