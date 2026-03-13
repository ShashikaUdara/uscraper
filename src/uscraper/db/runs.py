"""
Scrape runs API: insert run at start, update on completion.
Run metadata only; no scraped data stored in DB.
"""
from typing import Any, Dict, List, Optional

import sqlite3


def start_run(conn: sqlite3.Connection, profile_id: int, output_csv_path: str) -> int:
    """
    Insert a new scrape run with status 'running'.
    Returns the new run id.
    """
    cur = conn.execute(
        """
        INSERT INTO scrape_runs (profile_id, status, output_csv_path)
        VALUES (?, 'running', ?)
        """,
        (profile_id, output_csv_path),
    )
    conn.commit()
    return cur.lastrowid


def complete_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    row_count: Optional[int] = None,
) -> None:
    """
    Mark run as completed: status='completed', finished_at=now, optional row_count.
    """
    conn.execute(
        """
        UPDATE scrape_runs
        SET status = 'completed', finished_at = datetime('now'), row_count = ?
        WHERE id = ?
        """,
        (row_count, run_id),
    )
    conn.commit()


def fail_run(
    conn: sqlite3.Connection,
    run_id: int,
    error_message: Optional[str] = None,
) -> None:
    """
    Mark run as failed: status='failed', finished_at=now, error_message.
    """
    conn.execute(
        """
        UPDATE scrape_runs
        SET status = 'failed', finished_at = datetime('now'), error_message = ?
        WHERE id = ?
        """,
        (error_message or "", run_id),
    )
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: int) -> Optional[Dict[str, Any]]:
    """Return run by id."""
    row = conn.execute(
        """
        SELECT id, profile_id, started_at, finished_at, status,
               output_csv_path, error_message, row_count
        FROM scrape_runs WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    return dict(row) if row else None


def list_runs_for_profile(
    conn: sqlite3.Connection,
    profile_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return recent runs for a profile."""
    rows = conn.execute(
        """
        SELECT id, profile_id, started_at, finished_at, status,
               output_csv_path, error_message, row_count
        FROM scrape_runs WHERE profile_id = ?
        ORDER BY started_at DESC LIMIT ?
        """,
        (profile_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]
