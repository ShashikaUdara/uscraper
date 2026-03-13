"""
Scrape profiles and elements API: CRUD for scrape_profiles and scrape_elements.
"""
from typing import Any, Dict, List, Optional

import sqlite3


# --- Scrape profiles CRUD ---


def create_profile(
    conn: sqlite3.Connection,
    name: str,
    url: str,
    browser_id: int,
    options_json: Optional[str] = None,
) -> int:
    """
    Create a new scrape profile. Returns the new profile id.
    """
    cur = conn.execute(
        """
        INSERT INTO scrape_profiles (name, url, browser_id, options_json)
        VALUES (?, ?, ?, ?)
        """,
        (name, url, browser_id, options_json),
    )
    conn.commit()
    return cur.lastrowid


def get_profile(conn: sqlite3.Connection, profile_id: int) -> Optional[Dict[str, Any]]:
    """Return profile by id, or None."""
    row = conn.execute(
        """
        SELECT id, name, url, browser_id, options_json, created_at, updated_at
        FROM scrape_profiles WHERE id = ?
        """,
        (profile_id,),
    ).fetchone()
    return dict(row) if row else None


def list_profiles(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return all scrape profiles."""
    rows = conn.execute(
        """
        SELECT id, name, url, browser_id, options_json, created_at, updated_at
        FROM scrape_profiles ORDER BY updated_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def update_profile(
    conn: sqlite3.Connection,
    profile_id: int,
    *,
    name: Optional[str] = None,
    url: Optional[str] = None,
    browser_id: Optional[int] = None,
    options_json: Optional[str] = None,
) -> None:
    """
    Update profile fields. Only provided keyword arguments are updated.
    """
    updates = ["updated_at = datetime('now')"]
    params: List[Any] = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if url is not None:
        updates.append("url = ?")
        params.append(url)
    if browser_id is not None:
        updates.append("browser_id = ?")
        params.append(browser_id)
    if options_json is not None:
        updates.append("options_json = ?")
        params.append(options_json)
    params.append(profile_id)
    conn.execute(
        f"UPDATE scrape_profiles SET {', '.join(updates)} WHERE id = ?", params
    )
    conn.commit()


def delete_profile(conn: sqlite3.Connection, profile_id: int) -> None:
    """Delete a profile and its elements (CASCADE)."""
    conn.execute("DELETE FROM scrape_profiles WHERE id = ?", (profile_id,))
    conn.commit()


# --- Scrape elements CRUD ---


def add_element(
    conn: sqlite3.Connection,
    profile_id: int,
    selector: str,
    column_name: str,
    extract_type: str = "text",
    extract_arg: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> int:
    """
    Add a scrape element to a profile. Returns the new element id.
    extract_type: 'text' | 'attribute' | 'html'
    extract_arg: attribute name when extract_type is 'attribute'
    """
    if sort_order is None:
        next_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM scrape_elements WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()[0]
        sort_order = next_order
    cur = conn.execute(
        """
        INSERT INTO scrape_elements (profile_id, selector, extract_type, extract_arg, column_name, sort_order)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (profile_id, selector, extract_type, extract_arg, column_name, sort_order),
    )
    conn.commit()
    return cur.lastrowid


def get_elements_for_profile(
    conn: sqlite3.Connection, profile_id: int
) -> List[Dict[str, Any]]:
    """Return all scrape elements for a profile, ordered by sort_order."""
    rows = conn.execute(
        """
        SELECT id, profile_id, selector, extract_type, extract_arg, column_name, sort_order
        FROM scrape_elements WHERE profile_id = ?
        ORDER BY sort_order, id
        """,
        (profile_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def update_element(
    conn: sqlite3.Connection,
    element_id: int,
    *,
    selector: Optional[str] = None,
    column_name: Optional[str] = None,
    extract_type: Optional[str] = None,
    extract_arg: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> None:
    """Update an element. Only provided keyword arguments are updated."""
    updates = []
    params: List[Any] = []
    if selector is not None:
        updates.append("selector = ?")
        params.append(selector)
    if column_name is not None:
        updates.append("column_name = ?")
        params.append(column_name)
    if extract_type is not None:
        updates.append("extract_type = ?")
        params.append(extract_type)
    if extract_arg is not None:
        updates.append("extract_arg = ?")
        params.append(extract_arg)
    if sort_order is not None:
        updates.append("sort_order = ?")
        params.append(sort_order)
    if not updates:
        return
    params.append(element_id)
    conn.execute(
        f"UPDATE scrape_elements SET {', '.join(updates)} WHERE id = ?", params
    )
    conn.commit()


def delete_element(conn: sqlite3.Connection, element_id: int) -> None:
    """Delete a scrape element."""
    conn.execute("DELETE FROM scrape_elements WHERE id = ?", (element_id,))
    conn.commit()


def get_profile_with_elements(
    conn: sqlite3.Connection, profile_id: int
) -> Optional[Dict[str, Any]]:
    """Return profile and its elements as a single dict with 'elements' key."""
    profile = get_profile(conn, profile_id)
    if not profile:
        return None
    profile["elements"] = get_elements_for_profile(conn, profile_id)
    return profile
