"""
Structured logging: file under ~/.config/uscraper/logs/ and optional console.
Call setup_logging() once at application startup.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from uscraper.config import get_config_dir

LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "uscraper.log"


def setup_logging(
    level: int = logging.INFO,
    console: bool = True,
    log_dir: Optional[Path] = None,
) -> None:
    """
    Configure logging for the application.
    Writes to <config_dir>/logs/uscraper.log and optionally to stderr.
    """
    if log_dir is None:
        log_dir = get_config_dir() / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / LOG_FILE_NAME

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger("uscraper")
    root.setLevel(level)
    root.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        root.addHandler(ch)


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the uscraper namespace (for use as get_logger(__name__))."""
    if not name.startswith("uscraper"):
        name = f"uscraper.{name}"
    return logging.getLogger(name)
