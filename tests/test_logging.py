"""Tests for logging configuration."""
import logging
import pytest

from uscraper.logging_config import setup_logging, get_logger


def test_setup_logging_creates_log_dir_and_file(tmp_path):
    setup_logging(level=logging.DEBUG, console=False, log_dir=tmp_path)
    log_file = tmp_path / "uscraper.log"
    assert log_file.parent.exists()
    logger = get_logger("test")
    logger.info("test message")
    # Force flush
    for h in logger.handlers:
        h.flush()
    # Logger may be child of uscraper, so check root
    root = logging.getLogger("uscraper")
    for h in root.handlers:
        if getattr(h, "baseFilename", None):
            h.close()
    assert log_file.exists()
    assert "test message" in log_file.read_text()


def test_get_logger_returns_logger():
    log = get_logger("engine.runner")
    assert isinstance(log, logging.Logger)
    assert "uscraper" in log.name
