"""Tests for scraping engine: CSV export, runner with mocked browser."""
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from uscraper.engine import run_scrape, write_rows_to_csv
from uscraper.engine.runner import _extract_all_elements, _sanitize_filename, _profile_options
from uscraper.db import ensure_db, create_profile, add_element, update_driver, get_run


# --- Fake page for mocking Playwright ---


class _FakeElement:
    def __init__(self, data):
        self._data = data

    def text_content(self):
        return self._data.get("text", "")

    def get_attribute(self, name):
        return (self._data.get("attrs") or {}).get(name, "")

    def inner_html(self):
        return self._data.get("html", "")


class _FakeLocator:
    def __init__(self, data_list):
        self._data_list = data_list

    def count(self):
        return len(self._data_list)

    def nth(self, i):
        return _FakeElement(self._data_list[i])


class _FakePage:
    def __init__(self, locator_data):
        self._locator_data = locator_data

    def locator(self, selector):
        return _FakeLocator(self._locator_data.get(selector, []))

    def goto(self, url, **kwargs):
        pass

    def wait_for_load_state(self, *args, **kwargs):
        pass


# --- CSV export ---


def test_write_rows_to_csv(tmp_path):
    rows = [
        {"name": "Alice", "value": "1"},
        {"name": "Bob", "value": "2"},
    ]
    path = tmp_path / "out.csv"
    n = write_rows_to_csv(path, rows, ["name", "value"])
    assert n == 2
    content = path.read_text(encoding="utf-8")
    assert "name,value" in content
    assert "Alice,1" in content
    assert "Bob,2" in content


def test_write_rows_to_csv_creates_dir(tmp_path):
    path = tmp_path / "sub" / "out.csv"
    n = write_rows_to_csv(path, [{"a": "1"}], ["a"])
    assert n == 1
    assert path.exists()


# --- Runner helpers ---


def test_sanitize_filename():
    assert _sanitize_filename("My Profile") == "My Profile"
    assert _sanitize_filename("a/b:c") == "a_b_c"
    assert _sanitize_filename("") == "scrape"


def test_profile_options():
    assert _profile_options({}) == {}
    assert _profile_options({"options_json": '{"headless": false}'}) == {"headless": False}
    assert _profile_options({"options_json": "invalid"}) == {}


# --- Extraction with fake page ---


def test_extract_all_elements():
    page = _FakePage({
        "h1": [{"text": "Hello"}, {"text": "World"}],
        "a": [{"attrs": {"href": "http://a.com"}}, {"attrs": {"href": "http://b.com"}}],
    })
    elements = [
        {"id": 1, "selector": "h1", "extract_type": "text", "extract_arg": None, "column_name": "title", "sort_order": 0},
        {"id": 2, "selector": "a", "extract_type": "attribute", "extract_arg": "href", "column_name": "link", "sort_order": 1},
    ]
    rows, column_order = _extract_all_elements(page, elements)
    assert column_order == ["title", "link"]
    assert len(rows) == 2
    assert rows[0]["title"] == "Hello"
    assert rows[0]["link"] == "http://a.com"
    assert rows[1]["title"] == "World"
    assert rows[1]["link"] == "http://b.com"


def test_extract_all_elements_empty():
    page = _FakePage({"h1": []})
    elements = [{"id": 1, "selector": "h1", "extract_type": "text", "extract_arg": None, "column_name": "title", "sort_order": 0}]
    rows, column_order = _extract_all_elements(page, elements)
    assert rows == []
    assert column_order == ["title"]


# --- run_scrape with DB and mocked browser ---


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = ensure_db(db_path)
        yield conn
        conn.close()


def test_run_scrape_profile_not_found(temp_db):
    result = run_scrape(999, conn=temp_db)
    assert result["success"] is False
    assert "not found" in result["error_message"].lower()


def test_run_scrape_no_elements(temp_db):
    pid = create_profile(temp_db, "Empty", "https://example.com", browser_id=1)
    result = run_scrape(pid, conn=temp_db)
    assert result["success"] is False
    assert "no scrape elements" in result["error_message"].lower()


def test_run_scrape_browser_not_installed(temp_db):
    pid = create_profile(temp_db, "P", "https://example.com", browser_id=1)
    add_element(temp_db, pid, "h1", "title", extract_type="text")
    # driver is still 'pending' by default
    result = run_scrape(pid, conn=temp_db)
    assert result["success"] is False
    assert "not installed" in result["error_message"].lower()


def test_run_scrape_success(temp_db, tmp_path):
    from uscraper.db import set_config

    update_driver(temp_db, 1, install_status="installed", executable_path="playwright:chromium")
    set_config(temp_db, "output_dir", str(tmp_path))

    pid = create_profile(temp_db, "TestProfile", "https://example.com", browser_id=1)
    add_element(temp_db, pid, "h1", "title", extract_type="text")
    add_element(temp_db, pid, "a", "url", extract_type="attribute", extract_arg="href")

    fake_page = _FakePage({
        "h1": [{"text": "Hello"}, {"text": "World"}],
        "a": [{"attrs": {"href": "https://x.com/1"}}, {"attrs": {"href": "https://x.com/2"}}],
    })

    @contextmanager
    def fake_launch(*args, **kwargs):
        yield fake_page

    with patch("uscraper.engine.runner.launch_browser_from_driver", fake_launch):
        result = run_scrape(pid, conn=temp_db)

    assert result["success"] is True
    assert result["run_id"] is not None
    assert result["row_count"] == 2
    assert result["output_csv_path"].endswith(".csv")
    assert Path(result["output_csv_path"]).exists()
    content = Path(result["output_csv_path"]).read_text(encoding="utf-8")
    assert "title" in content and "url" in content
    assert "Hello" in content and "World" in content

    run = get_run(temp_db, result["run_id"])
    assert run["status"] == "completed"
    assert run["row_count"] == 2
