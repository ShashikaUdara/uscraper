"""
Element picker: open a URL in a browser, inject click-to-select behavior,
and return a stable CSS selector for each element the user clicks.
Persist selections to a scrape profile via DB (add_element).
"""
import queue
import threading
from typing import Any, Dict, List, Optional

import sqlite3

from uscraper.engine.playwright_driver import launch_browser_from_driver
from uscraper.engine.selector import get_selector_for_element_js


# Sentinel put in queue when session is closed (internal)
_PICKER_CLOSED = object()

# Public sentinel: get_next_selector returns this when the session is closed (user closed browser).
# Use "if sel is PICKER_CLOSED: break" in the loop; do not break on None (timeout).
PICKER_CLOSED = object()


class ElementPickerSession:
    """
    Picker session: browser at URL with injected click listener.
    Each click returns a CSS selector via get_next_selector().
    Use as context manager; call get_next_selector() in a loop until it returns None.
    """

    def __init__(
        self,
        url: str,
        executable_path: str,
        options: Optional[Dict[str, Any]] = None,
    ):
        self._url = url
        self._executable_path = executable_path
        self._options = dict(options or {})
        self._options.setdefault("headless", False)
        self._page = None
        self._queue = queue.Queue()
        self._closed = False
        self._browser_cm = None

    def _on_element_clicked(self, selector: str) -> None:
        if self._closed:
            return
        self._queue.put(selector)

    def __enter__(self) -> "ElementPickerSession":
        self._browser_cm = launch_browser_from_driver(
            self._executable_path, self._options
        )
        self._page = self._browser_cm.__enter__()
        self._page.goto(self._url, wait_until="domcontentloaded", timeout=30000)
        self._page.add_init_script(get_selector_for_element_js())
        self._page.evaluate(get_selector_for_element_js())

        self._page.expose_function(
            "__pickerCallback",
            lambda s: self._on_element_clicked(s) if isinstance(s, str) else None,
        )

        inject_click_js = """
        (function() {
          if (window.__pickerInjected) return;
          window.__pickerInjected = true;
          document.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof window.__getSelector === 'function' && typeof window.__pickerCallback === 'function') {
              try {
                window.__pickerCallback(window.__getSelector(e.target));
              } catch (err) {}
            }
          }, true);
        })();
        """
        self._page.evaluate(inject_click_js)
        # Daemon thread: when user closes the browser, put sentinel so the loop can exit
        self._close_check_stop = threading.Event()
        def _watch_closed():
            while not self._close_check_stop.wait(0.7):
                if self._closed:
                    break
                try:
                    if self._page:
                        self._page.evaluate("1")
                except Exception:
                    self._closed = True
                    try:
                        self._queue.put_nowait(_PICKER_CLOSED)
                    except queue.Full:
                        pass
                    break
        self._close_check_thread = threading.Thread(target=_watch_closed, daemon=True)
        self._close_check_thread.start()
        return self

    def __exit__(self, *args) -> None:
        self._closed = True
        if getattr(self, "_close_check_stop", None) is not None:
            self._close_check_stop.set()
        self._queue.put(_PICKER_CLOSED)
        if self._browser_cm is not None:
            self._browser_cm.__exit__(*args)
            self._browser_cm = None
        self._page = None

    @property
    def page(self):
        """Playwright Page for the picker browser (e.g. for GUI to embed or drive)."""
        return self._page

    def get_next_selector(self, timeout: Optional[float] = None):
        """
        Block until the user clicks an element, or timeout, or session is closed.
        Returns the CSS selector (str) when the user clicked an element.
        Returns None if timeout expires (no click yet — keep polling).
        Returns PICKER_CLOSED when the session was closed (exit the loop).
        """
        if self._closed:
            return PICKER_CLOSED
        try:
            result = self._queue.get(timeout=timeout)
            if result is _PICKER_CLOSED:
                return PICKER_CLOSED
            return result
        except queue.Empty:
            return None

    def close(self) -> None:
        """Signal that the session is done (puts sentinel so get_next_selector returns None)."""
        self._closed = True
        try:
            self._queue.put_nowait(_PICKER_CLOSED)
        except queue.Full:
            pass

    def add_to_profile(
        self,
        conn: sqlite3.Connection,
        profile_id: int,
        selector: str,
        column_name: str,
        extract_type: str = "text",
        extract_arg: Optional[str] = None,
    ) -> int:
        """
        Persist a picked element to the given profile (append to scrape_elements).
        Returns the new element id. Convenience that calls db add_element.
        """
        from uscraper.db.profiles import add_element as db_add_element
        return db_add_element(
            conn, profile_id, selector, column_name,
            extract_type=extract_type, extract_arg=extract_arg,
        )


def list_profile_elements(conn: sqlite3.Connection, profile_id: int) -> list:
    """Return scrape_elements for the profile (for picker UI list). Delegates to db.profiles."""
    from uscraper.db.profiles import get_elements_for_profile
    return get_elements_for_profile(conn, profile_id)


def remove_profile_element(conn: sqlite3.Connection, element_id: int) -> None:
    """Remove a scrape element by id. Delegates to db.profiles."""
    from uscraper.db.profiles import delete_element
    delete_element(conn, element_id)


def reorder_profile_elements(
    conn: sqlite3.Connection, profile_id: int, element_ids_in_order: List[int]
) -> None:
    """Update sort_order of elements to match the given id order (0-based index = sort_order)."""
    from uscraper.db.profiles import update_element
    for sort_order, element_id in enumerate(element_ids_in_order):
        update_element(conn, element_id, sort_order=sort_order)
