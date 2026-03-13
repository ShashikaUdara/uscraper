"""
Application configuration paths and environment.
Uses ~/.config/uscraper/ for DB and config on first run.
"""
import os
from pathlib import Path


def get_config_dir() -> Path:
    """Return the application config directory, creating it if needed."""
    path = Path.home() / ".config" / "uscraper"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Return the SQLite database file path."""
    return get_config_dir() / "uscraper.db"
