import sqlite3
import sqlite_vec
from app.config import settings


def setup_connection() -> sqlite3.Connection:
    """Return a raw sqlite3 connection with sqlite-vec loaded."""
    conn = sqlite3.connect(str(settings.db_path))
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn
