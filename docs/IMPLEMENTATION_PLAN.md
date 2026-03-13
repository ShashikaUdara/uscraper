# Universal Web Scraper (uscraper) — Implementation Plan

## Executive Summary

This document describes the implementation plan for a **universal, customizable web scraping desktop application** that supports multiple browsers and operating systems. The **first phase targets Linux (Ubuntu)** only. The desktop application will be implemented in **Python** for a single-language stack and straightforward Ubuntu packaging. Web scraping will use Python-based browser automation. Application state and configuration will live in **SQLite**; scraped data will be exported as **CSV files** (one per scraping run), not stored in the application database.

---

## 0. Implementation Progress

| Phase | Status | Notes |
|-------|--------|--------|
| **Phase 0** | Pending | Project layout partially done (see Phase 1); full bootstrap in progress. |
| **Phase 1** | **Done** | Database and configuration layer implemented (see below). |
| **Phase 2** | **Done** | Browser/driver auto-install implemented (see below). |
| **Phase 3** | **Done** | Scraping engine implemented (see below). |
| **Phase 4** | **Done** | Element selection mechanism (picker) implemented (see below). |
| Phase 5 | Pending | Desktop GUI. |
| Phase 6 | Pending | Ubuntu packaging. |
| Phase 7 | Pending | Testing and polish. |

### Phase 1 — Completed

- **1.1 Schema:** `src/uscraper/db/schema.sql` — all tables and indexes (CREATE IF NOT EXISTS).
- **1.2 DB connection:** `src/uscraper/db/connection.py` — `get_connection()`, `init_schema()`, `ensure_db()`; config path via `src/uscraper/config.py` (`~/.config/uscraper/`); WAL mode and foreign keys enabled.
- **1.3 App config API:** `src/uscraper/db/app_config.py` — `get_config()`, `set_config()`, `get_config_default()`.
- **1.4 Browsers and drivers API:** `src/uscraper/db/browsers.py` — CRUD for browsers/drivers; `seed_browsers_if_empty()` seeds Chromium, Firefox, WebKit (Playwright) with `install_status = 'pending'`; `ensure_db()` calls seed after schema.
- **1.5 Scrape profiles API:** `src/uscraper/db/profiles.py` — full CRUD for `scrape_profiles` and `scrape_elements`; `get_profile_with_elements()` for engine use.
- **1.6 Scrape runs API:** `src/uscraper/db/runs.py` — `start_run()`, `complete_run()`, `fail_run()`, `get_run()`, `list_runs_for_profile()`.
- **Deliverables:** DB layer has no GUI dependency. **Unit tests:** `tests/test_db.py` (22 tests) — schema creation, ensure_db + seed, app_config, browsers/drivers, profiles/elements, runs; all passing. Package: `pyproject.toml` with `src` layout; entry point `uscraper` in `src/uscraper/__main__.py` (stub that initializes DB).

### Phase 2 — Completed

- **2.1 Browser list in DB:** Already seeded in Phase 1 (chromium, firefox, webkit, driver_type='playwright').
- **2.2 Install flow:** `ensure_browser_installed(conn, browser_id)` in `src/uscraper/db/browsers.py` — if `install_status != 'installed'`, calls Playwright install via `src/uscraper/browser_install.py` (`install_playwright_browser(internal_name)` runs `python -m playwright install <browser>`); on success updates `drivers` with `install_status='installed'` and `executable_path='playwright:<name>'`.
- **2.3 Driver path:** Executable path stored as marker `playwright:<internal_name>` for engine to use Playwright API; optional `get_playwright_cache_path()` for display.
- **2.4 Error handling:** On install failure, `install_status='failed'` and `install_error_message` set; `ensure_browser_installed` returns `(False, error_message)`. Schema: `drivers.install_error_message` added (with migration in `connection._migrate_drivers_table` for existing DBs).
- **2.5 Selenium:** Deferred (optional).
- **Deliverables:** Selecting a browser triggers install when needed; driver info persisted in SQLite. **Tests:** 4 new tests in `test_db.py` (already installed, success/failure mocked, unknown browser). **Makefile:** `make help`, `venv`, `install`, `install-dev`, `test`, `run`, `install-browsers`, `install-deps`, `clean`.

### Phase 3 — Completed

- **3.1 Engine interface:** `run_scrape(profile_id, conn=None)` in `src/uscraper/engine/runner.py` — loads profile with elements from DB, resolves browser/driver, builds output path from `app_config.output_dir` (default `~/.config/uscraper/scrapes`), calls `start_run()`, launches browser, navigates, extracts, writes CSV, then `complete_run()` or `fail_run()`; returns result dict (`success`, `run_id`, `output_csv_path`, `row_count`, `error_message`).
- **3.2 Browser launch:** `src/uscraper/engine/playwright_driver.py` — `launch_browser_from_driver(executable_path, options)` context manager; parses `playwright:chromium` marker, uses `launch_playwright_page(internal_name, options)` with sync Playwright; options from profile `options_json`: `headless`, `timeout`, `viewport`.
- **3.3 Page load:** `page.goto(url, wait_until='domcontentloaded')`, then `page.wait_for_load_state('networkidle')` with configurable timeout.
- **3.4 Element extraction:** For each `scrape_elements` row, `_extract_column_values(page, selector, extract_type, extract_arg)` uses `page.locator(selector)` and for each match returns text, attribute, or HTML; `_extract_all_elements(page, elements)` builds rectangular rows (max length across columns, pad with `""`).
- **3.5 CSV generation:** `src/uscraper/engine/csv_export.py` — `write_rows_to_csv(path, rows, column_order)` UTF-8; path pattern `scrape_{profile_name}_{YYYY-MM-DD_HH-MM-SS}.csv`; `row_count` and `output_csv_path` updated in `scrape_runs`.
- **3.6 Concurrency:** Single run per `run_scrape` call; no queue (optional later).
- **Deliverables:** Engine produces CSV per run and updates DB. **Tests:** `tests/test_engine.py` (10 tests) — CSV export, `_sanitize_filename`, `_profile_options`, `_extract_all_elements` with fake page, `run_scrape` for profile not found / no elements / browser not installed / success with mocked browser; fixture `tests/fixtures/sample.html` for reference.

### Phase 4 — Completed

- **4.1 Picker mode:** `ElementPickerSession` in `src/uscraper/engine/picker.py` — context manager that launches browser (headless=False) via `launch_browser_from_driver`, loads URL, injects click listener; user clicks in the page and each click is reported as a CSS selector via `get_next_selector()` (blocking queue).
- **4.2 Selector generation:** `src/uscraper/engine/selector.py` — injectable JS (`get_selector_for_element_js()`) defines `window.__getSelector(el)`: uses `id` with `CSS.escape` if unique, else builds path from root using `tag:nth-child(n)`; optional `compute_selector_via_page(page, element_handle)` for Python-side use.
- **4.3 Extract type and column:** For each picked element the caller (e.g. GUI) supplies column name and extract type (text/attribute/html) and optional attribute name; `session.add_to_profile(conn, profile_id, selector, column_name, extract_type, extract_arg)` persists to `scrape_elements`.
- **4.4 Persist to profile:** `add_to_profile()` delegates to `db.profiles.add_element` with `sort_order` auto-incremented; list/remove/reorder use DB APIs.
- **4.5 List and remove:** `list_profile_elements(conn, profile_id)`, `remove_profile_element(conn, element_id)`, `reorder_profile_elements(conn, profile_id, element_ids_in_order)` in `picker.py` delegate to `db.profiles` (get_elements_for_profile, delete_element, update_element).
- **Deliverables:** Point-and-click selection produces stable selectors; selections stored in SQLite. **Tests:** `tests/test_picker.py` (6 tests) — selector JS non-empty, list/remove/reorder elements, `add_to_profile` without browser, optional integration test for selector validity in real browser (skipped if Chromium not installed).

---

## 1. Technology Choices

| Concern | Choice | Rationale |
|--------|--------|-----------|
| **Desktop application** | **Python** | Single language with scraping stack; rich GUI (PyQt6 or custom Tk); easy packaging (pip, PyInstaller, .deb); fast iteration. |
| **Web scraping** | **Python** (Playwright or Selenium) | Mature ecosystem; multi-browser support; good Linux support; easy integration with desktop app. |
| **Configuration & state** | **SQLite** | Single-file, no server; suitable for app config, driver registry, scrape profiles. |
| **Scraped data** | **CSV per run** | No DB bloat; portable; one file per run with timestamp/naming convention. |
| **Target OS (Phase 1)** | **Linux (Ubuntu)** | Single platform first; installable via pip, optional .deb or AppImage. |

**Browser automation recommendation:** Prefer **Playwright** for Python: built-in browser install (chromium, firefox, webkit), stable APIs, and good selector/element introspection for the “select what to scrape” feature.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Desktop Application (Python)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   GUI       │  │  Config     │  │  Scraper    │  │  CSV Export     │  │
│  │  (PyQt6/    │  │  Manager    │  │  Engine     │  │  (per run)      │  │
│  │   Tkinter)  │  │             │  │  (Python)   │  │                 │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                │                    │          │
│         └────────────────┼────────────────┼────────────────────┘          │
│                          ▼                ▼                              │
│                 ┌────────────────────────────────────┐                   │
│                 │  SQLite DB (config, drivers,       │                   │
│                 │  scrape profiles, run metadata)    │                   │
│                 └────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                 ┌────────────────────────────────────┐
                 │  Browser binaries (Playwright/       │
                 │  Chromium, Firefox, etc.)           │
                 └────────────────────────────────────┘
```

- **GUI:** URL input, browser selection, element picker, run controls, output path.
- **Config Manager:** Read/write app and driver config from SQLite; manage “installed” browsers/drivers.
- **Scraper Engine:** Launch selected browser, load URL, apply selected elements/selectors, extract data, hand off to CSV export.
- **SQLite:** All persistent app and driver configuration; no scraped content stored in DB.
- **CSV:** One file per scraping run (e.g. `scrape_<profile>_<timestamp>.csv`).

---

## 3. SQLite Database Design

**Location:** e.g. `~/.config/uscraper/uscraper.db` (or under project in dev). Single DB file.

**Principles:** Normalized tables; clear naming; separate tables for app config, browser/driver registry, scrape profiles, and run metadata (no scraped payload in DB).

### 3.1 Tables Overview

| Table | Purpose |
|-------|--------|
| `app_config` | Key-value application settings (theme, default output dir, last window size, etc.). |
| `browsers` | Registered browser types (e.g. chromium, firefox, webkit) and display names. |
| `drivers` | Driver/binary info per browser: path, version, install status, last_used. |
| `scrape_profiles` | Named profiles: URL, list of selectors, browser_id, options. |
| `scrape_elements` | Elements to scrape per profile: selector, attribute/text, column name, order. |
| `scrape_runs` | Metadata for each run: profile_id, started_at, output_csv_path, status. |

### 3.2 Schema (SQL)

```sql
-- Application-wide key-value configuration
CREATE TABLE app_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Browser types (e.g. chromium, firefox, webkit)
CREATE TABLE browsers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  internal_name TEXT UNIQUE NOT NULL,   -- e.g. 'chromium', 'firefox'
  display_name TEXT NOT NULL,
  driver_type TEXT NOT NULL,            -- 'playwright' or 'selenium'
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Installed driver/binary per browser (version, path, status)
CREATE TABLE drivers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  browser_id INTEGER NOT NULL REFERENCES browsers(id) ON DELETE CASCADE,
  version TEXT,
  executable_path TEXT,
  install_status TEXT NOT NULL DEFAULT 'pending',  -- 'pending'|'installed'|'failed'
  last_used_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(browser_id)
);

-- Scrape profile: URL + which browser + options
CREATE TABLE scrape_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  browser_id INTEGER NOT NULL REFERENCES browsers(id),
  options_json TEXT,                   -- headless, timeout, etc.
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Elements to scrape within a profile (selector → column)
CREATE TABLE scrape_elements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL REFERENCES scrape_profiles(id) ON DELETE CASCADE,
  selector TEXT NOT NULL,
  extract_type TEXT NOT NULL,          -- 'text'|'attribute'|'html'
  extract_arg TEXT,                   -- attribute name if extract_type='attribute'
  column_name TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(profile_id, column_name)
);

-- Run metadata only (no scraped data)
CREATE TABLE scrape_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL REFERENCES scrape_profiles(id),
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT,
  status TEXT NOT NULL DEFAULT 'running',  -- 'running'|'completed'|'failed'
  output_csv_path TEXT NOT NULL,
  error_message TEXT,
  row_count INTEGER
);

CREATE INDEX idx_scrape_elements_profile ON scrape_elements(profile_id);
CREATE INDEX idx_scrape_runs_profile ON scrape_runs(profile_id);
```

**Notes:**
- All config and driver information is in these tables; scraped content is only written to CSV.
- `drivers` holds one row per browser (or per channel if we later support multiple versions); `executable_path` and `install_status` support “auto-install” and reuse.

---

## 4. CSV Export Convention

- **No scraped data in SQLite.** Each run produces one CSV file.
- **Path pattern:** Configurable base directory (stored in `app_config`), e.g.  
  `{output_dir}/scrape_{profile_name}_{YYYY-MM-DD_HH-MM-SS}.csv`
- **Content:** Header row = column names from `scrape_elements.column_name`; one row per matched element (or per combined row if we group by a parent selector). Encoding: UTF-8.

---

## 5. Phases and Detailed Tasks

### Phase 0: Project Bootstrap and Environment (Linux/Ubuntu)

**Goal:** Reproducible dev environment and project layout.

| # | Task | Details |
|---|------|--------|
| 0.1 | Repository layout | Create directories: `src/` (main package), `src/gui/`, `src/engine/`, `src/db/`, `tests/`, `docs/`, `scripts/` (e.g. install scripts). |
| 0.2 | Python environment | Require Python 3.10+; `pyproject.toml` + `requirements.txt` or PEP 517 build; virtualenv recommended. |
| 0.3 | Dependencies | Add: GUI (PyQt6 or tkinter), Playwright, `sqlite3` (stdlib), pandas or csv for CSV write. Document system deps (e.g. Qt libs for PyQt6 on Ubuntu). |
| 0.4 | Config path | Implement `~/.config/uscraper/` for DB and config; ensure directory exists on first run. |
| 0.5 | Entry point | Single entry script (e.g. `python -m uscraper` or `uscraper` console script) that launches GUI. |

**Deliverables:** Clean repo structure, dependency list, runnable stub that opens GUI and creates DB path.

---

### Phase 1: Database and Configuration Layer

**Goal:** SQLite schema in place and all app/driver configuration read and written through a clear API.

| # | Task | Details |
|---|------|--------|
| 1.1 | Schema creation | Implement schema in `src/db/schema.sql` and apply on first run (create tables and indexes if not exist). |
| 1.2 | DB connection | Module in `src/db/` to open SQLite (e.g. `~/.config/uscraper/uscraper.db`), with optional WAL mode. |
| 1.3 | App config API | Get/set `app_config` (e.g. `get_config(key)`, `set_config(key, value)`). |
| 1.4 | Browsers and drivers API | CRUD for `browsers` and `drivers`; seed initial rows for Playwright browsers (chromium, firefox, webkit) with `install_status = 'pending'`. |
| 1.5 | Scrape profiles API | CRUD for `scrape_profiles` and `scrape_elements`; ensure referential integrity. |
| 1.6 | Scrape runs API | Insert `scrape_runs` at start; update on completion (status, `output_csv_path`, `row_count`, `error_message`). |

**Deliverables:** Database layer with no GUI dependency; unit tests for CRUD and schema.

---

### Phase 2: Browser and Driver Management (Auto-Install)

**Goal:** User can select a browser from a list; if not installed, the application installs it (e.g. via Playwright) and records it in `drivers`.

| # | Task | Details |
|---|------|--------|
| 2.1 | Browser list in DB | Ensure `browsers` table is seeded with Playwright browser entries (internal_name, display_name, driver_type='playwright'). |
| 2.2 | Install flow | On “Use this browser” (or first use): if `drivers.install_status != 'installed'`, call Playwright’s install (e.g. `playwright install chromium`); update `drivers` with path and `install_status = 'installed'`. |
| 2.3 | Driver path resolution | After install, resolve executable path (Playwright stores under user dir); persist in `drivers.executable_path` and optionally `last_used_at`. |
| 2.4 | Error handling | If install fails, set `install_status = 'failed'` and store message; surface in GUI. |
| 2.5 | Optional: Selenium fallback | If scope permits, add one browser entry with driver_type='selenium' and similar install (e.g. webdriver-manager); same `drivers` table. |

**Deliverables:** Selecting a browser from the list triggers install when needed; driver info is stored in SQLite and reused.

---

### Phase 3: Scraping Engine (Python)

**Goal:** Headless (or headed) browser loads a URL; applies selectors from a profile; extracts data; returns structured rows and writes CSV.

| # | Task | Details |
|---|------|--------|
| 3.1 | Engine interface | Single entry point, e.g. `run_scrape(profile_id)`: load profile and elements from DB, resolve driver, run browser, extract, write CSV, update `scrape_runs`. |
| 3.2 | Browser launch | Use Playwright (async or sync) with browser from `drivers`; apply options from `scrape_profiles.options_json` (headless, viewport, timeout). |
| 3.3 | Page load and wait | Navigate to profile URL; optional wait for network idle or selector; configurable timeout. |
| 3.4 | Element extraction | For each `scrape_elements` row: evaluate selector; apply `extract_type` (text, attribute, html); map to `column_name`. Handle multiple matches (e.g. rows from table: one CSV row per match set or per row depending on design). |
| 3.5 | CSV generation | Build table of rows (list of dict or columns); write one CSV per run to path from convention; set `output_csv_path` and `row_count` in `scrape_runs`. |
| 3.6 | Concurrency | Prefer one run at a time per application instance to avoid resource contention; optional queue later. |

**Deliverables:** Engine that, given a profile_id, produces a CSV and updates DB; unit tests with a static HTML fixture.

---

### Phase 4: Element Selection Mechanism (Picker)

**Goal:** User can visually select which components/elements to scrape; selections are stored as `scrape_elements` for the current profile.

| # | Task | Details |
|---|------|--------|
| 4.1 | Picker mode | In GUI, “Select elements” opens the target URL in a controlled browser (or embedded view); user hovers/clicks to select elements. |
| 4.2 | Selector generation | On click, use Playwright (or devtools) to compute a stable selector (e.g. unique CSS selector or data attributes); optionally allow user to edit selector text. |
| 4.3 | Extract type and column | For each selected element, user chooses: text / attribute (with name) / html; and a column name for CSV. |
| 4.4 | Persist to profile | Save selections as `scrape_elements` for current `scrape_profiles` row; sort_order by selection order. |
| 4.5 | List and remove | Show list of selected elements; allow remove or reorder; sync to DB. |

**Deliverables:** User can point-and-click to define what to scrape; selectors and column mapping stored in SQLite.

---

### Phase 5: Desktop GUI (Linux)

**Goal:** Full UI for URL input, profile management, browser selection, element picker, and run.

| # | Task | Details |
|---|------|--------|
| 5.1 | Framework choice | PyQt6 or Tkinter; document choice and Ubuntu packages (e.g. `python3-pyqt6` or `python3-tk`). |
| 5.2 | Main window | Layout: URL bar, browser dropdown (from `browsers`), “Install”/“Use” for selected browser, “Select elements” button, “Run scrape” button, status bar, optional output path display. |
| 5.3 | Profile handling | Create/save/load profile: name, URL, browser; load/save from `scrape_profiles` and `scrape_elements`. |
| 5.4 | Browser dropdown | Populate from DB; on select, show install status; trigger Phase 2 install if needed. |
| 5.5 | Element picker UI | Integrate Phase 4: open picker, show selected elements list, persist to profile. |
| 5.6 | Run and progress | On “Run scrape”, call engine; show progress (e.g. “Loading…”, “Extracting…”, “Writing CSV”); on success show path and row count; on failure show error from `scrape_runs.error_message`. |
| 5.7 | Settings | Simple settings dialog: default output directory (saved in `app_config`), optional theme/locale. |

**Deliverables:** Usable GUI on Ubuntu for the full flow: URL → browser → pick elements → run → CSV.

---

### Phase 6: Ubuntu Installability and Packaging

**Goal:** Application is installable on Ubuntu (e.g. 22.04 LTS) via standard methods.

| # | Task | Details |
|---|------|--------|
| 6.1 | System dependencies | Document: Python 3.10+, and for Playwright system libs (e.g. `playwright install-deps`); Qt if PyQt6. |
| 6.2 | pip install | `pyproject.toml` with dependencies and console script `uscraper`; user can `pip install .` or `pip install -e .` in venv. |
| 6.3 | Optional .deb | Script or small packaging (e.g. `stdeb` or manual `dpkg-buildpackage`) to produce .deb that installs Python package + launcher; optional. |
| 6.4 | Optional AppImage | PyInstaller or similar to produce single executable; run script to build AppImage; optional. |
| 6.5 | First-run | On first launch, create `~/.config/uscraper/`, initialize DB, optionally run `playwright install` for default browser. |
| 6.6 | README | Install instructions for Ubuntu: venv, pip, system deps, and how to run `uscraper`. |

**Deliverables:** Clear install steps; at minimum `pip install` + run; optional .deb/AppImage for convenience.

---

### Phase 7: Testing and Polish

**Goal:** Reliable behavior and clear error handling.

| # | Task | Details |
|---|------|--------|
| 7.1 | Unit tests | DB layer, config API, engine with mock/fixture HTML. |
| 7.2 | Integration test | One full run: create profile, add elements, run scrape, assert CSV exists and has expected columns. |
| 7.3 | Error handling | Timeouts, invalid selector, browser crash: update `scrape_runs.status` and `error_message`; show in GUI. |
| 7.4 | Logging | Structured logging to file under `~/.config/uscraper/logs/` (or similar) and optional console. |

**Deliverables:** Test suite, robust error reporting, basic logging.

---

## 6. Directory Structure (Proposed)

```
uscraper/
├── pyproject.toml
├── requirements.txt
├── README.md
├── docs/
│   └── IMPLEMENTATION_PLAN.md
├── src/
│   └── uscraper/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py          # paths, env
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   ├── schema.sql
│       │   ├── app_config.py
│       │   ├── browsers.py
│       │   ├── profiles.py
│       │   └── runs.py
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── runner.py       # run_scrape(profile_id)
│       │   ├── playwright_driver.py
│       │   └── csv_export.py
│       └── gui/
│           ├── __init__.py
│           ├── main_window.py
│           ├── browser_select.py
│           ├── element_picker.py
│           └── profile_editor.py
├── tests/
│   ├── test_db.py
│   ├── test_engine.py
│   └── fixtures/
├── scripts/
│   └── install_deps_ubuntu.sh  # optional
└── packaging/                 # optional .deb / AppImage
```

---

## 7. Risk and Scope Control

- **Scope (Phase 1):** Linux only; one automation backend (Playwright first). Selenium can be added later using same DB and GUI.
- **Risks:** Playwright install requires network and system libs; we document and optionally run `playwright install-deps` in install script. Dynamic sites may need explicit waits or optional JS execution—covered in profile options.
- **Out of scope for Phase 1:** Saving scraped data in DB, multi-OS installers, cloud or distributed runs.

---

## 8. Success Criteria (Phase 1)

1. **Installable** on Ubuntu (documented pip + system deps).
2. **Configurable** via SQLite: URL, browser, and selected elements per profile.
3. **Browser selection** from list with automatic install and persistence in `drivers`.
4. **Element selection** via picker and stored in `scrape_elements`.
5. **Scraping** produces one CSV per run; run metadata in `scrape_runs`; no scraped data in DB.
6. **Clean DB:** Normalized schema, all driver and app config in SQLite.

---

## 9. Next Steps After Review

1. Confirm technology choices (Python desktop + Playwright, SQLite, CSV).
2. Confirm schema and CSV output convention.
3. Prioritize or split any phase (e.g. minimal GUI first vs. full picker).
4. Begin implementation with Phase 0 and Phase 1, then Phase 2 and 3, then GUI (Phase 4–5), then packaging and testing (Phase 6–7).

---

*Document version: 1.4 — Phase 1–4 implemented; progress tracked in §0.*
