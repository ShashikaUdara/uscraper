-- Application-wide key-value configuration
CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Browser types (e.g. chromium, firefox, webkit)
CREATE TABLE IF NOT EXISTS browsers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  internal_name TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  driver_type TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Installed driver/binary per browser (version, path, status)
CREATE TABLE IF NOT EXISTS drivers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  browser_id INTEGER NOT NULL REFERENCES browsers(id) ON DELETE CASCADE,
  version TEXT,
  executable_path TEXT,
  install_status TEXT NOT NULL DEFAULT 'pending',
  install_error_message TEXT,
  last_used_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(browser_id)
);

-- Scrape profile: URL + which browser + options
CREATE TABLE IF NOT EXISTS scrape_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  browser_id INTEGER NOT NULL REFERENCES browsers(id),
  options_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Elements to scrape within a profile (selector → column)
CREATE TABLE IF NOT EXISTS scrape_elements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL REFERENCES scrape_profiles(id) ON DELETE CASCADE,
  selector TEXT NOT NULL,
  extract_type TEXT NOT NULL,
  extract_arg TEXT,
  column_name TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(profile_id, column_name)
);

-- Run metadata only (no scraped data)
CREATE TABLE IF NOT EXISTS scrape_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  profile_id INTEGER NOT NULL REFERENCES scrape_profiles(id),
  started_at TEXT NOT NULL DEFAULT (datetime('now')),
  finished_at TEXT,
  status TEXT NOT NULL DEFAULT 'running',
  output_csv_path TEXT NOT NULL,
  error_message TEXT,
  row_count INTEGER
);

CREATE INDEX IF NOT EXISTS idx_scrape_elements_profile ON scrape_elements(profile_id);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_profile ON scrape_runs(profile_id);
