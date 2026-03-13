"""
Playwright driver: launch browser from driver_type and options.
Uses executable_path marker "playwright:chromium" etc. from Phase 2.
"""
from contextlib import contextmanager
from typing import Any, Dict, Iterator

from playwright.sync_api import Page, sync_playwright

from uscraper.browser_install import PLAYWRIGHT_PATH_PREFIX


def _parse_executable_marker(executable_path: str | None) -> str | None:
    """If executable_path is 'playwright:chromium', return 'chromium'. Else None."""
    if not executable_path or not executable_path.startswith(PLAYWRIGHT_PATH_PREFIX):
        return None
    return executable_path[len(PLAYWRIGHT_PATH_PREFIX) :].strip() or None


@contextmanager
def launch_playwright_page(
    internal_name: str,
    options: Dict[str, Any] | None = None,
) -> Iterator[Page]:
    """
    Launch a Playwright browser and yield the page. Closes browser and playwright on exit.
    internal_name: 'chromium' | 'firefox' | 'webkit'
    options: optional dict with headless (bool), timeout (int ms), viewport (dict width/height).
    """
    options = options or {}
    headless = options.get("headless", True)
    timeout_ms = options.get("timeout", 30000)
    viewport = options.get("viewport")

    pw = sync_playwright().start()
    try:
        if internal_name == "chromium":
            browser = pw.chromium.launch(headless=headless)
        elif internal_name == "firefox":
            browser = pw.firefox.launch(headless=headless)
        elif internal_name == "webkit":
            browser = pw.webkit.launch(headless=headless)
        else:
            pw.stop()
            raise ValueError(f"Unknown browser: {internal_name}")

        try:
            context_options = {"ignore_https_errors": True}
            if viewport:
                context_options["viewport"] = viewport
            context = browser.new_context(**context_options)
            context.set_default_timeout(timeout_ms)
            page = context.new_page()
            yield page
        finally:
            browser.close()
    finally:
        pw.stop()


@contextmanager
def launch_browser_from_driver(
    executable_path: str | None,
    options: Dict[str, Any] | None = None,
) -> Iterator[Page]:
    """
    Launch browser using driver's executable_path (e.g. 'playwright:chromium').
    Yields a Playwright Page. Closes browser on exit.
    """
    internal_name = _parse_executable_marker(executable_path)
    if not internal_name:
        raise ValueError(
            f"Unsupported executable_path for Playwright: {executable_path!r}. "
            "Expected playwright:chromium, playwright:firefox, or playwright:webkit."
        )
    with launch_playwright_page(internal_name, options) as page:
        yield page
