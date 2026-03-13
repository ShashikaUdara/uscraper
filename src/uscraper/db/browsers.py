"""
Browsers and drivers API: CRUD for browsers and drivers tables.
Seeds Playwright browsers (chromium, firefox, webkit) with install_status 'pending'.
"""
from typing import Any, Dict, List, Optional

import sqlite3

# Default Playwright browser entries to seed
PLAYWRIGHT_BROWSERS = [
    {"internal_name": "chromium", "display_name": "Chromium", "driver_type": "playwright"},
    {"internal_name": "firefox", "display_name": "Firefox", "driver_type": "playwright"},
    {"internal_name": "webkit", "display_name": "WebKit", "driver_type": "playwright"},
]


def seed_browsers_if_empty(conn: sqlite3.Connection) -> None:
    """
    Insert default Playwright browser rows into browsers and drivers
    if the browsers table is empty. Idempotent.
    """
    if conn.execute("SELECT COUNT(*) FROM browsers").fetchone()[0] > 0:
        return
    for b in PLAYWRIGHT_BROWSERS:
        conn.execute(
            """
            INSERT INTO browsers (internal_name, display_name, driver_type)
            VALUES (?, ?, ?)
            """,
            (b["internal_name"], b["display_name"], b["driver_type"]),
        )
    conn.commit()
    # Create one driver row per browser with pending status
    for b in PLAYWRIGHT_BROWSERS:
        cur = conn.execute(
            "SELECT id FROM browsers WHERE internal_name = ?", (b["internal_name"],)
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                """
                INSERT INTO drivers (browser_id, install_status)
                VALUES (?, 'pending')
                """,
                (row[0],),
            )
    conn.commit()


# --- Browsers CRUD ---


def list_browsers(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Return all browsers with their driver info (id, internal_name, display_name,
    driver_type, install_status, executable_path, version, last_used_at).
    """
    rows = conn.execute(
        """
        SELECT b.id, b.internal_name, b.display_name, b.driver_type,
               d.install_status, d.executable_path, d.version, d.last_used_at
        FROM browsers b
        LEFT JOIN drivers d ON d.browser_id = b.id
        ORDER BY b.id
        """
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_browser_by_id(conn: sqlite3.Connection, browser_id: int) -> Optional[Dict[str, Any]]:
    """
    Return one browser by id with driver info, or None.
    """
    row = conn.execute(
        """
        SELECT b.id, b.internal_name, b.display_name, b.driver_type,
               d.id AS driver_id, d.install_status, d.executable_path, d.version, d.last_used_at
        FROM browsers b
        LEFT JOIN drivers d ON d.browser_id = b.id
        WHERE b.id = ?
        """,
        (browser_id,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_browser_by_internal_name(
    conn: sqlite3.Connection, internal_name: str
) -> Optional[Dict[str, Any]]:
    """Return one browser by internal_name with driver info, or None."""
    row = conn.execute(
        "SELECT id FROM browsers WHERE internal_name = ?", (internal_name,)
    ).fetchone()
    if not row:
        return None
    return get_browser_by_id(conn, row["id"])


# --- Drivers CRUD ---


def update_driver(
    conn: sqlite3.Connection,
    browser_id: int,
    *,
    version: Optional[str] = None,
    executable_path: Optional[str] = None,
    install_status: Optional[str] = None,
    last_used_at: Optional[str] = None,
) -> None:
    """
    Update the driver row for the given browser_id.
    Only provided keyword arguments are updated.
    """
    updates = []
    params: List[Any] = []
    if version is not None:
        updates.append("version = ?")
        params.append(version)
    if executable_path is not None:
        updates.append("executable_path = ?")
        params.append(executable_path)
    if install_status is not None:
        updates.append("install_status = ?")
        params.append(install_status)
    if last_used_at is not None:
        updates.append("last_used_at = ?")
        params.append(last_used_at)
    if not updates:
        return
    params.append(browser_id)
    conn.execute(
        f"UPDATE drivers SET {', '.join(updates)} WHERE browser_id = ?", params
    )
    conn.commit()


def set_driver_last_used(conn: sqlite3.Connection, browser_id: int) -> None:
    """Set last_used_at to now for the driver of the given browser."""
    conn.execute(
        "UPDATE drivers SET last_used_at = datetime('now') WHERE browser_id = ?",
        (browser_id,),
    )
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row) if row else {}
