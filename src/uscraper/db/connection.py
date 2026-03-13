"""
Database connection and schema initialization.
Opens SQLite at ~/.config/uscraper/uscraper.db and applies schema on first run.
"""
import sqlite3
from pathlib import Path
from typing import Optional

from uscraper.config import get_db_path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Open a connection to the application SQLite database.
    Creates the config directory and database file if they do not exist.
    Enables WAL mode for better concurrent read behavior.
    """
    path = db_path if db_path is not None else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Apply schema.sql to the given connection.
    Idempotent: uses CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    conn.executescript(schema_sql)
    conn.commit()


def ensure_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get a connection and ensure schema is applied; seeds default browsers if empty.
    Use this for application startup or first access.
    """
    from uscraper.db.browsers import seed_browsers_if_empty

    conn = get_connection(db_path)
    init_schema(conn)
    seed_browsers_if_empty(conn)
    return conn
