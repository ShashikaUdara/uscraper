"""Tests for element picker: selector generation, session add_to_profile, list/remove/reorder, inspection."""
import tempfile
from pathlib import Path

import pytest

from uscraper.engine import (
    ElementPickerSession,
    PICKER_CLOSED,
    list_profile_elements,
    remove_profile_element,
    reorder_profile_elements,
    get_selector_for_element_js,
)
from uscraper.engine.picker import get_picker_hover_highlight_js
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


def test_hover_highlight_js_returns_expected_content():
    """Phase 5a: hover highlight script contains class and elementFromPoint."""
    js = get_picker_hover_highlight_js()
    assert isinstance(js, str)
    assert "uscraper-picker-highlight" in js
    assert "elementFromPoint" in js
    assert "__pickerHoverInjected" in js
    assert "mousemove" in js
    assert "mouseout" in js
    assert len(js) > 200


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


def test_picker_callback_with_inspection_payload_returns_tuple():
    """When the browser sends a full inspection dict, get_next_selector returns (selector, inspection)."""
    session = ElementPickerSession("https://example.com", "playwright:chromium")
    payload = {
        "selector": "a#main.nav",
        "tagName": "a",
        "attributes": [{"name": "href", "value": "https://example.com"}],
        "innerTextPreview": "Home",
        "htmlPreview": "<a id=\"main\">Home</a>",
    }
    session._on_element_clicked(payload)
    result = session.get_next_selector(timeout=0.1)
    assert result is not None and result is not PICKER_CLOSED
    selector, inspection, hierarchy = result
    assert selector == "a#main.nav"
    assert inspection is not None
    assert inspection.tag_name == "a"
    assert len(inspection.attributes) == 1
    assert inspection.attributes[0]["name"] == "href"
    assert inspection.inner_text_preview == "Home"


def test_picker_callback_with_plain_string_returns_selector_and_none_inspection():
    """Backward compat: when callback receives only a selector string, inspection is None."""
    session = ElementPickerSession("https://example.com", "playwright:chromium")
    session._on_element_clicked("div > span:nth-child(1)")
    result = session.get_next_selector(timeout=0.1)
    assert result is not None and result is not PICKER_CLOSED
    selector, inspection, hierarchy = result
    assert selector == "div > span:nth-child(1)"
    assert inspection is None
    assert hierarchy is None


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


def test_inspection_js_returns_payload_in_browser():
    """Integration: load fixture, inject getInspection, verify payload shape."""
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    fixture_path = Path(__file__).parent / "fixtures" / "sample.html"
    if not fixture_path.exists():
        pytest.skip("fixture sample.html not found")
    url = "file://" + str(fixture_path.resolve())

    from uscraper.engine.selector import get_selector_for_element_js
    from uscraper.engine.inspect import get_element_inspection_js, ElementInspection

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception:
            pytest.skip("Chromium not installed")
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=5000)
            page.evaluate(get_selector_for_element_js())
            page.evaluate(get_element_inspection_js())
            payload = page.evaluate("""() => {
                var el = document.querySelector('h1');
                return el && window.__getInspection ? window.__getInspection(el) : null;
            }""")
            assert payload is not None
            assert "selector" in payload
            assert "tagName" in payload
            assert payload.get("tagName") == "h1"
            assert "attributes" in payload
            assert "innerTextPreview" in payload
            insp = ElementInspection.from_browser_dict(payload)
            assert insp is not None
            assert insp.tag_name == "h1"
            assert insp.selector == payload["selector"]
        finally:
            browser.close()
