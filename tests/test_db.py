"""Unit tests for DB layer: schema, app_config, browsers, drivers, profiles, runs."""
import sqlite3
import pytest

from uscraper.db import (
    ensure_db,
    get_connection,
    init_schema,
    get_config,
    set_config,
    get_config_default,
    seed_browsers_if_empty,
    list_browsers,
    get_browser_by_id,
    get_browser_by_internal_name,
    update_driver,
    set_driver_last_used,
    create_profile,
    get_profile,
    list_profiles,
    update_profile,
    delete_profile,
    add_element,
    get_elements_for_profile,
    update_element,
    delete_element,
    get_profile_with_elements,
    start_run,
    complete_run,
    fail_run,
    get_run,
    list_runs_for_profile,
)


# --- Schema and connection ---


def test_schema_creates_tables(conn_empty):
    """Schema creates all expected tables."""
    cur = conn_empty.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    assert "app_config" in tables
    assert "browsers" in tables
    assert "drivers" in tables
    assert "scrape_profiles" in tables
    assert "scrape_elements" in tables
    assert "scrape_runs" in tables


def test_ensure_db_applies_schema_and_seeds(temp_db_path):
    """ensure_db applies schema and seeds browsers."""
    conn = ensure_db(temp_db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM browsers").fetchone()[0]
        assert count == 3  # chromium, firefox, webkit
        count_d = conn.execute("SELECT COUNT(*) FROM drivers").fetchone()[0]
        assert count_d == 3
    finally:
        conn.close()


# --- App config ---


def test_get_config_missing_returns_none(conn):
    get_config(conn, "nonexistent") is None


def test_set_config_and_get_config(conn):
    set_config(conn, "theme", "dark")
    assert get_config(conn, "theme") == "dark"
    set_config(conn, "theme", "light")
    assert get_config(conn, "theme") == "light"


def test_get_config_default(conn):
    assert get_config_default(conn, "missing", "default") == "default"
    set_config(conn, "key", "value")
    assert get_config_default(conn, "key", "default") == "value"


# --- Browsers and drivers ---


def test_seed_browsers_if_empty_idempotent(conn_empty):
    seed_browsers_if_empty(conn_empty)
    count1 = conn_empty.execute("SELECT COUNT(*) FROM browsers").fetchone()[0]
    seed_browsers_if_empty(conn_empty)
    count2 = conn_empty.execute("SELECT COUNT(*) FROM browsers").fetchone()[0]
    assert count1 == count2 == 3


def test_list_browsers(conn):
    browsers = list_browsers(conn)
    assert len(browsers) == 3
    names = [b["internal_name"] for b in browsers]
    assert "chromium" in names
    assert "firefox" in names
    assert "webkit" in names
    for b in browsers:
        assert b["install_status"] == "pending"


def test_get_browser_by_id(conn):
    b = get_browser_by_id(conn, 1)
    assert b is not None
    assert b["internal_name"] == "chromium"
    assert get_browser_by_id(conn, 999) is None


def test_get_browser_by_internal_name(conn):
    b = get_browser_by_internal_name(conn, "firefox")
    assert b is not None
    assert b["display_name"] == "Firefox"
    assert get_browser_by_internal_name(conn, "nonexistent") is None


def test_update_driver(conn):
    update_driver(conn, 1, install_status="installed", executable_path="/usr/bin/chromium")
    browsers = list_browsers(conn)
    chromium = next(b for b in browsers if b["internal_name"] == "chromium")
    assert chromium["install_status"] == "installed"
    assert chromium["executable_path"] == "/usr/bin/chromium"


def test_set_driver_last_used(conn):
    set_driver_last_used(conn, 1)
    row = conn.execute("SELECT last_used_at FROM drivers WHERE browser_id = 1").fetchone()
    assert row[0] is not None


# --- Profiles and elements ---


def test_create_profile(conn):
    pid = create_profile(conn, "Test Profile", "https://example.com", browser_id=1)
    assert pid > 0
    p = get_profile(conn, pid)
    assert p["name"] == "Test Profile"
    assert p["url"] == "https://example.com"
    assert p["browser_id"] == 1


def test_update_profile(conn):
    pid = create_profile(conn, "Old", "https://a.com", browser_id=1)
    update_profile(conn, pid, name="New", url="https://b.com")
    p = get_profile(conn, pid)
    assert p["name"] == "New"
    assert p["url"] == "https://b.com"


def test_list_profiles(conn):
    create_profile(conn, "P1", "https://a.com", browser_id=1)
    create_profile(conn, "P2", "https://b.com", browser_id=2)
    profiles = list_profiles(conn)
    assert len(profiles) >= 2


def test_delete_profile(conn):
    pid = create_profile(conn, "ToDelete", "https://x.com", browser_id=1)
    delete_profile(conn, pid)
    assert get_profile(conn, pid) is None


def test_add_element_and_get_elements(conn):
    pid = create_profile(conn, "E", "https://e.com", browser_id=1)
    eid = add_element(conn, profile_id=pid, selector="h1", column_name="title", extract_type="text")
    assert eid > 0
    add_element(conn, profile_id=pid, selector="a", column_name="link", extract_type="attribute", extract_arg="href")
    elements = get_elements_for_profile(conn, pid)
    assert len(elements) == 2
    titles = [e["column_name"] for e in elements]
    assert "title" in titles
    assert "link" in titles


def test_update_element(conn):
    pid = create_profile(conn, "U", "https://u.com", browser_id=1)
    eid = add_element(conn, profile_id=pid, selector="h1", column_name="title", extract_type="text")
    update_element(conn, eid, selector="h2", column_name="heading")
    elements = get_elements_for_profile(conn, pid)
    assert len(elements) == 1
    assert elements[0]["selector"] == "h2"
    assert elements[0]["column_name"] == "heading"


def test_delete_element(conn):
    pid = create_profile(conn, "D", "https://d.com", browser_id=1)
    eid = add_element(conn, profile_id=pid, selector="h1", column_name="title", extract_type="text")
    delete_element(conn, eid)
    assert get_elements_for_profile(conn, pid) == []


def test_get_profile_with_elements(conn):
    pid = create_profile(conn, "Full", "https://f.com", browser_id=1)
    add_element(conn, profile_id=pid, selector="h1", column_name="title", extract_type="text")
    full = get_profile_with_elements(conn, pid)
    assert full is not None
    assert full["name"] == "Full"
    assert len(full["elements"]) == 1
    assert full["elements"][0]["column_name"] == "title"


# --- Runs ---


def test_start_run_complete_run(conn):
    pid = create_profile(conn, "R", "https://r.com", browser_id=1)
    run_id = start_run(conn, profile_id=pid, output_csv_path="/tmp/out.csv")
    assert run_id > 0
    r = get_run(conn, run_id)
    assert r["status"] == "running"
    complete_run(conn, run_id, row_count=10)
    r = get_run(conn, run_id)
    assert r["status"] == "completed"
    assert r["row_count"] == 10
    assert r["finished_at"] is not None


def test_start_run_fail_run(conn):
    pid = create_profile(conn, "F", "https://f.com", browser_id=1)
    run_id = start_run(conn, profile_id=pid, output_csv_path="/tmp/fail.csv")
    fail_run(conn, run_id, error_message="Timeout")
    r = get_run(conn, run_id)
    assert r["status"] == "failed"
    assert r["error_message"] == "Timeout"


def test_list_runs_for_profile(conn):
    pid = create_profile(conn, "L", "https://l.com", browser_id=1)
    start_run(conn, profile_id=pid, output_csv_path="/tmp/1.csv")
    start_run(conn, profile_id=pid, output_csv_path="/tmp/2.csv")
    runs = list_runs_for_profile(conn, profile_id=pid, limit=10)
    assert len(runs) == 2
