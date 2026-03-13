# uscraper — Universal Web Scraper
# Common commands for development and testing on Linux/Ubuntu

PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
PIP := $(BIN)/pip
PYTEST := $(BIN)/pytest

.PHONY: help venv install install-dev test run clean install-browsers install-deps

help:
	@echo "uscraper Makefile targets:"
	@echo "  venv            Create virtualenv at .venv"
	@echo "  install         Install package (editable) and runtime deps"
	@echo "  install-dev     Install with [dev] (pytest, etc.)"
	@echo "  test            Run tests"
	@echo "  run             Run uscraper (DB init only until GUI is ready)"
	@echo "  install-browsers  Install Playwright browsers (chromium, firefox, webkit)"
	@echo "  install-deps    Install system deps for Playwright (Ubuntu: playwright install-deps)"
	@echo "  clean           Remove .venv, cache, and build artifacts"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(PIP) install -e .

install-dev: venv
	$(PIP) install -e ".[dev]"

test: install-dev
	$(PYTEST) tests/ -v

run: install
	$(BIN)/uscraper

install-browsers: install
	$(BIN)/python -m playwright install

install-deps: install
	$(BIN)/python -m playwright install-deps

clean:
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf src/*.egg-info
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
