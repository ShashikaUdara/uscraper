# uscraper

Universal web scraper — desktop tool for Linux (Ubuntu).

## Install on Ubuntu

**Requirements:** Python 3.10+, Tkinter (`python3-tk`), Playwright system libs.

```bash
sudo apt install -y python3 python3-venv python3-tk
make venv && make install
make install-deps          # Playwright system dependencies
make install-browsers      # Optional: download Chromium/Firefox/WebKit
make run
```

Full details and troubleshooting: **[docs/INSTALL.md](docs/INSTALL.md)**.

## Run (with GUI)

```bash
make run
# or: .venv/bin/uscraper
```

## Flow

1. Create or select a **profile** (name, URL, browser).
2. **Install** the selected browser if needed (Playwright Chromium/Firefox/WebKit).
3. Click **Select elements**: a browser window opens at the URL; click elements to add them (column name, extract type: text/attribute/html).
4. Click **Run scrape** to extract data and save one CSV per run under the output directory (set in **File → Settings**).
