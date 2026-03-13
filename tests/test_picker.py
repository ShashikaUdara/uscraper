"""Tests for element picker: selector generation, session add_to_profile, list/remove/reorder."""
import tempfile
from pathlib import Path

import pytest

from uscraper.engine import (
    ElementPickerSession,
    list_profile_elements,
    remove_profile_element,
    reorder_profile_elements,
    get_selector_for_element_js,
)
from uscraper.db import ensure_db, create_profile, get_elements_for_profile


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = ensure_db(db_path)
        yield conn
        conn.close()


def test_get_selector_js_returns_non_empty():
    js = get_selector_for_element_js()
    assert isinstance(js, str)
    assert "__getSelector" in js
    assert len(js) > 100


def test_list_profile_elements(temp_db):
    pid = create_profile(temp_db, "P", "https://example.com", browser_id=1)
    assert list_profile_elements(temp_db, pid) == []
    from uscraper.db import add_element
    add_element(temp_db, pid, "h1", "title", extract_type="text")
    els = list_profile_elements(temp_db, pid)
    assert len(els) == 1
    assert els[0]["selector"] == "h1"
    assert els[0]["column_name"] == "title"


def test_remove_profile_element(temp_db):
    pid = create_profile(temp_db, "P", "https://example.com", browser_id=1)
    from uscraper.db import add_element
    eid = add_element(temp_db, pid, "h1", "title", extract_type="text")
    assert len(list_profile_elements(temp_db, pid)) == 1
    remove_profile_element(temp_db, eid)
    assert len(list_profile_elements(temp_db, pid)) == 0


def test_reorder_profile_elements(temp_db):
    pid = create_profile(temp_db, "P", "https://example.com", browser_id=1)
    from uscraper.db import add_element
    e1 = add_element(temp_db, pid, "h1", "title", extract_type="text")
    e2 = add_element(temp_db, pid, "a", "link", extract_type="attribute", extract_arg="href")
    els = get_elements_for_profile(temp_db, pid)
    assert els[0]["column_name"] == "title"
    assert els[1]["column_name"] == "link"
    reorder_profile_elements(temp_db, pid, [e2, e1])
    els2 = get_elements_for_profile(temp_db, pid)
    assert els2[0]["column_name"] == "link"
    assert els2[1]["column_name"] == "title"


def test_picker_add_to_profile_without_browser(temp_db):
    """add_to_profile persists to DB without needing to open the browser."""
    pid = create_profile(temp_db, "P", "https://example.com", browser_id=1)
    session = ElementPickerSession("https://example.com", "playwright:chromium")
    eid = session.add_to_profile(temp_db, pid, "h1", "title", extract_type="text")
    assert eid > 0
    els = list_profile_elements(temp_db, pid)
    assert len(els) == 1
    assert els[0]["selector"] == "h1"
    assert els[0]["column_name"] == "title"
    assert els[0]["extract_type"] == "text"


def test_selector_generates_valid_selector_in_browser(temp_db):
    """Integration: load fixture HTML, inject getSelector, verify selector matches element."""
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    fixture_path = Path(__file__).parent / "fixtures" / "sample.html"
    if not fixture_path.exists():
        pytest.skip("fixture sample.html not found")
    url = "file://" + str(fixture_path.resolve())

    js = get_selector_for_element_js()

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception:
            pytest.skip("Chromium not installed")
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=5000)
            page.evaluate(js)
            # Get selector for first h1
            selector = page.evaluate("""() => {
                var el = document.querySelector('h1');
                return el && window.__getSelector ? window.__getSelector(el) : '';
            }""")
            assert isinstance(selector, str)
            assert len(selector) > 0
            # Verify the selector matches the same element
            match = page.evaluate("""(sel) => {
                try { return document.querySelector(sel) && document.querySelector(sel).tagName === 'H1'; }
                catch (e) { return false; }
            }""", selector)
            assert match is True
        finally:
            browser.close()
