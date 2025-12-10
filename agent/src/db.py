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
