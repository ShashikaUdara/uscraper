"""
Browser auto-install: run Playwright install for a given browser and resolve path.
Used when user selects a browser that is not yet installed.
"""
import subprocess
import sys
from pathlib import Path
from typing import Tuple

# Playwright stores browsers under this relative path (Linux default)
# We use a marker path for the engine: "playwright:<internal_name>"
PLAYWRIGHT_PATH_PREFIX = "playwright:"


def install_playwright_browser(internal_name: str) -> Tuple[bool, str | None, str | None]:
    """
    Run `python -m playwright install <internal_name>` for the given browser.
    Returns (success, executable_path_or_marker, error_message).
    On success executable_path is "playwright:<internal_name>" for engine to use.
    """
    if internal_name not in ("chromium", "firefox", "webkit"):
        return False, None, f"Unknown Playwright browser: {internal_name}"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", internal_name],
            capture_output=True,
            text=True,
            timeout=600,
            env={**__import__("os").environ},
        )
    except subprocess.TimeoutExpired as e:
        return False, None, f"Install timed out: {e}"
    except FileNotFoundError:
        return False, None, "Playwright not found. Install with: pip install playwright"
    except Exception as e:
        return False, None, str(e)

    if result.returncode != 0:
        err = result.stderr or result.stdout or "Unknown error"
        return False, None, err.strip() or f"Exit code {result.returncode}"

    # Engine will use this marker to launch via Playwright API
    path_marker = f"{PLAYWRIGHT_PATH_PREFIX}{internal_name}"
    return True, path_marker, None


def get_playwright_cache_path() -> Path:
    """Return the default Playwright browser cache directory (e.g. for display)."""
    return Path.home() / ".cache" / "ms-playwright"
