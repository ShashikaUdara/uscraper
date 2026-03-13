"""
App config API: get/set key-value application settings in app_config table.
"""
from typing import Optional

import sqlite3


def get_config(conn: sqlite3.Connection, key: str) -> Optional[str]:
    """
    Return the value for the given config key, or None if not set.
    """
    row = conn.execute(
        "SELECT value FROM app_config WHERE key = ?", (key,)
    ).fetchone()
    return row["value"] if row else None


def set_config(conn: sqlite3.Connection, key: str, value: str) -> None:
    """
    Set a config key to the given value (insert or replace).
    """
    conn.execute(
        """
        INSERT INTO app_config (key, value, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = datetime('now')
        """,
        (key, value),
    )
    conn.commit()


def get_config_default(conn: sqlite3.Connection, key: str, default: str) -> str:
    """
    Return the value for the given config key, or default if not set.
    """
    val = get_config(conn, key)
    return val if val is not None else default
