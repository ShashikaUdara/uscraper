"""
Element picker: open a URL in a browser, inject click-to-select behavior,
and return a stable CSS selector and optional element inspection for each click.
Persist selections to a scrape profile via DB (add_element).
Must be used from a single thread (Playwright sync API is not thread-safe).
"""
import queue
from typing import Any, Dict, List, Optional, Tuple, Union

import sqlite3

from uscraper.engine.inspect import (
    ElementHierarchy,
    ElementInspection,
    get_element_hierarchy_js,
    get_element_inspection_js,
)
from uscraper.engine.playwright_driver import launch_browser_from_driver
from uscraper.engine.selector import get_selector_for_element_js


# Sentinel put in queue when session is closed (internal)
_PICKER_CLOSED = object()

# Public sentinel: get_next_selector returns this when the session is closed (user closed browser).
# Use "if sel is PICKER_CLOSED: break" in the loop; do not break on None (timeout).
PICKER_CLOSED = object()


def get_picker_hover_highlight_js() -> str:
    """
    Return JavaScript that highlights the element under the cursor in the picker (Phase 5a).
    Listens to mousemove, uses elementFromPoint, applies a CSS class for outline highlight.
    Throttles via requestAnimationFrame; removes highlight on mouseout from window.
    """
    return r"""
(function() {
  if (window.__pickerHoverInjected) return;
  window.__pickerHoverInjected = true;
  var style = document.createElement('style');
  style.textContent = '.uscraper-picker-highlight { outline: 2px solid #2196F3 !important; outline-offset: 2px !important; }';
  document.head.appendChild(style);
  var lastHighlighted = null;
  var rafScheduled = false;
  var lastX = 0, lastY = 0;
  function updateHighlight() {
    rafScheduled = false;
    var el = document.elementFromPoint(lastX, lastY);
    if (el === lastHighlighted) return;
    if (lastHighlighted) {
      try { lastHighlighted.classList.remove('uscraper-picker-highlight'); } catch (e) {}
      lastHighlighted = null;
    }
    if (el && el.nodeType === 1 && el !== document.documentElement && el !== document.body) {
      try {
        el.classList.add('uscraper-picker-highlight');
        lastHighlighted = el;
      } catch (e) {}
    }
  }
  function onMove(e) {
    lastX = e.clientX;
    lastY = e.clientY;
    if (!rafScheduled) {
      rafScheduled = true;
      requestAnimationFrame(updateHighlight);
    }
  }
  function onOut(e) {
    if (!e.relatedTarget || !document.body.contains(e.relatedTarget)) {
      if (lastHighlighted) {
        try { lastHighlighted.classList.remove('uscraper-picker-highlight'); } catch (e) {}
        lastHighlighted = null;
      }
    }
  }
  document.addEventListener('mousemove', onMove, true);
  document.addEventListener('mouseout', onOut, true);
})();
""".strip()


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

    def _on_element_clicked(self, payload: Union[str, dict]) -> None:
        if self._closed:
            return
        if isinstance(payload, str):
            self._queue.put((payload, None, None, None))
            return
        if isinstance(payload, dict):
            inspection = ElementInspection.from_browser_dict(payload)
            selector = inspection.selector if inspection else (payload.get("selector") or "")
            hierarchy_data = payload.get("hierarchy")
            hierarchy = ElementHierarchy.from_browser_dict(hierarchy_data) if hierarchy_data else None
            match_count = payload.get("matchCount")
            if match_count is not None and not isinstance(match_count, int):
                try:
                    match_count = int(match_count)
                except (TypeError, ValueError):
                    match_count = None
            self._queue.put((selector, inspection, hierarchy, match_count))
            return
        self._queue.put(("", None, None, None))

    def __enter__(self) -> "ElementPickerSession":
        self._browser_cm = launch_browser_from_driver(
            self._executable_path, self._options
        )
        self._page = self._browser_cm.__enter__()
        self._page.goto(self._url, wait_until="domcontentloaded", timeout=30000)
        self._page.add_init_script(get_selector_for_element_js())
        self._page.evaluate(get_selector_for_element_js())
        self._page.evaluate(get_element_inspection_js())
        self._page.evaluate(get_element_hierarchy_js())

        self._page.expose_function(
            "__pickerCallback",
            lambda p: self._on_element_clicked(p) if p is not None else None,
        )

        inject_click_js = """
        (function() {
          if (window.__pickerInjected) return;
          window.__pickerInjected = true;
          document.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof window.__pickerCallback !== 'function') return;
            try {
              var el = e.target;
              if (typeof window.__getInspection === 'function') {
                var payload = window.__getInspection(el);
                if (!payload) payload = { selector: window.__getSelector ? window.__getSelector(el) : '' };
                if (typeof window.__getHierarchy === 'function') {
                  try { payload.hierarchy = window.__getHierarchy(el); } catch (hErr) {}
                }
                try {
                  var sel = payload.selector || '';
                  if (sel) payload.matchCount = document.querySelectorAll(sel).length;
                } catch (mcErr) {}
                window.__pickerCallback(payload);
              } else if (typeof window.__getSelector === 'function') {
                window.__pickerCallback({ selector: window.__getSelector(el) });
              }
            } catch (err) {}
          }, true);
        })();
        """
        self._page.evaluate(inject_click_js)
        # Phase 5a: hover highlight so user sees which element they are about to select
        self._page.evaluate(get_picker_hover_highlight_js())
        return self

    def __exit__(self, *args) -> None:
        self._closed = True
        self._queue.put(_PICKER_CLOSED)
        if self._browser_cm is not None:
            self._browser_cm.__exit__(*args)
            self._browser_cm = None
        self._page = None

    @property
    def page(self):
        """Playwright Page for the picker browser (e.g. for GUI to embed or drive)."""
        return self._page

    def get_next_selector(
        self, timeout: Optional[float] = None
    ) -> Union[Tuple[str, Optional[ElementInspection], Optional[ElementHierarchy], Optional[int]], None]:
        """
        Block until the user clicks an element, or timeout, or session is closed.
        Returns (selector, inspection, hierarchy, match_count) when the user clicked an element.
        inspection, hierarchy, and match_count may be None if unavailable.
        Returns None if timeout expires (no click yet — keep polling).
        Returns PICKER_CLOSED when the session was closed (exit the loop).
        """
        if self._closed:
            return PICKER_CLOSED
        try:
            result = self._queue.get(timeout=timeout)
            if result is _PICKER_CLOSED:
                return PICKER_CLOSED
            return result  # (selector, inspection, hierarchy, match_count)
        except queue.Empty:
            return None

    def close(self) -> None:
        """Signal that the session is done (puts sentinel so get_next_selector returns PICKER_CLOSED)."""
        self._closed = True
        try:
            self._queue.put_nowait(_PICKER_CLOSED)  # internal sentinel
        except queue.Full:
            pass

    def is_page_closed(self) -> bool:
        """Return True if the browser page is closed (e.g. user closed the window). Safe to call from same thread as session."""
        if self._closed or self._page is None:
            return True
        try:
            self._page.evaluate("1")
            return False
        except Exception:
            return True

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
