"""Pytest fixtures: temporary DB for tests."""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from uscraper.db import ensure_db, get_connection, init_schema
from uscraper.db.browsers import seed_browsers_if_empty


@pytest.fixture
def temp_db_path():
    """Return a temporary directory path; DB file will be created there."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test.db"


@pytest.fixture
def conn(temp_db_path):
    """Return a connection to an initialized temporary DB (schema + seed)."""
    c = ensure_db(temp_db_path)
    yield c
    c.close()


@pytest.fixture
def conn_empty(temp_db_path):
    """Return a connection with schema only, no browser seed (for seed tests)."""
    c = get_connection(temp_db_path)
    init_schema(c)
    yield c
    c.close()
