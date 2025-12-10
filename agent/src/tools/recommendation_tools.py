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
