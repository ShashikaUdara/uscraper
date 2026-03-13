"""
Scraping engine: single entry point run_scrape(profile_id).
Loads profile and elements from DB, launches browser, extracts data, writes CSV, updates scrape_runs.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlite3

from uscraper.config import get_config_dir
from uscraper.db import (
    ensure_db,
    get_config_default,
    get_profile_with_elements,
    get_browser_by_id,
    start_run,
    complete_run,
    fail_run,
)
from uscraper.engine.csv_export import write_rows_to_csv
from uscraper.engine.playwright_driver import launch_browser_from_driver


# Config key for default CSV output directory
OUTPUT_DIR_CONFIG_KEY = "output_dir"


def _default_output_dir() -> Path:
    """Default directory for scraped CSV files."""
    return get_config_dir() / "scrapes"


def _sanitize_filename(name: str) -> str:
    """Replace unsafe characters for use in CSV filename."""
    return re.sub(r'[^\w\-_. ]', "_", name).strip() or "scrape"


def _profile_options(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Parse profile.options_json into a dict for Playwright (headless, timeout, viewport)."""
    raw = profile.get("options_json")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return dict(data) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_column_values(page, selector: str, extract_type: str, extract_arg: Optional[str]) -> List[str]:
    """
    Extract all matching elements from page into a list of strings.
    extract_type: 'text' | 'attribute' | 'html'
    """
    locator = page.locator(selector)
    count = locator.count()
    values = []
    for i in range(count):
        el = locator.nth(i)
        if extract_type == "text":
            values.append((el.text_content() or "").strip())
        elif extract_type == "attribute":
            attr = extract_arg or "href"
            values.append(el.get_attribute(attr) or "")
        elif extract_type == "html":
            values.append(el.inner_html() or "")
        else:
            values.append((el.text_content() or "").strip())
    return values


def _extract_all_elements(page, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract data for each element definition; return list of row dicts.
    Each element defines selector, extract_type, extract_arg, column_name.
    Columns are aligned by max length; shorter columns are padded with "".
    """
    column_order = [e["column_name"] for e in sorted(elements, key=lambda x: (x["sort_order"], x["id"]))]
    columns: Dict[str, List[str]] = {}
    for el in elements:
        values = _extract_column_values(
            page,
            el["selector"],
            el["extract_type"],
            el.get("extract_arg"),
        )
        columns[el["column_name"]] = values

    max_rows = max(len(v) for v in columns.values()) if columns else 0
    if max_rows == 0:
        return [], column_order

    rows = []
    for i in range(max_rows):
        row = {}
        for col in column_order:
            vals = columns.get(col, [])
            row[col] = vals[i] if i < len(vals) else ""
        rows.append(row)
    return rows, column_order


def run_scrape(
    profile_id: int,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Run a scrape for the given profile_id: load profile, launch browser, extract, write CSV.
    If conn is not provided, uses ensure_db() and does not close it.
    Returns a result dict with keys: success (bool), run_id (int|None), output_csv_path (str|None),
    row_count (int|None), error_message (str|None).
    """
    own_conn = None
    if conn is None:
        conn = ensure_db()
        own_conn = conn

    try:
        profile = get_profile_with_elements(conn, profile_id)
        if not profile:
            return {
                "success": False,
                "run_id": None,
                "output_csv_path": None,
                "row_count": None,
                "error_message": "Profile not found",
            }
        elements = profile.get("elements") or []
        if not elements:
            return {
                "success": False,
                "run_id": None,
                "output_csv_path": None,
                "row_count": None,
                "error_message": "Profile has no scrape elements defined",
            }

        browser = get_browser_by_id(conn, profile["browser_id"])
        if not browser:
            return {
                "success": False,
                "run_id": None,
                "output_csv_path": None,
                "row_count": None,
                "error_message": "Browser not found",
            }
        if (browser.get("install_status") or "") != "installed":
            return {
                "success": False,
                "run_id": None,
                "output_csv_path": None,
                "row_count": None,
                "error_message": "Browser is not installed. Install it from the browser list first.",
            }

        output_dir = Path(
            get_config_default(conn, OUTPUT_DIR_CONFIG_KEY, str(_default_output_dir()))
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = _sanitize_filename(profile["name"])
        csv_path = output_dir / f"scrape_{safe_name}_{timestamp}.csv"

        run_id = start_run(conn, profile_id, str(csv_path))
        options = _profile_options(profile)

        try:
            with launch_browser_from_driver(browser.get("executable_path"), options) as page:
                page.goto(profile["url"], wait_until="domcontentloaded", timeout=options.get("timeout", 30000))
                page.wait_for_load_state("networkidle", timeout=options.get("timeout", 10000))

                rows, column_order = _extract_all_elements(page, elements)
                write_rows_to_csv(csv_path, rows, column_order)
                complete_run(conn, run_id, row_count=len(rows))

            return {
                "success": True,
                "run_id": run_id,
                "output_csv_path": str(csv_path),
                "row_count": len(rows),
                "error_message": None,
            }
        except Exception as e:
            fail_run(conn, run_id, str(e))
            return {
                "success": False,
                "run_id": run_id,
                "output_csv_path": str(csv_path),
                "row_count": None,
                "error_message": str(e),
            }
    finally:
        if own_conn:
            own_conn.close()
