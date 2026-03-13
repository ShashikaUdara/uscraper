# uscraper

Universal web scraper — desktop tool for Linux (Ubuntu).

## Run (with GUI)

```bash
# Install (creates venv, installs package + deps)
make install-dev

# On Ubuntu: Tkinter is required for the GUI
sudo apt install python3-tk

# Run the application
make run
# or: uscraper
```

## Flow

1. Create or select a **profile** (name, URL, browser).
2. **Install** the selected browser if needed (Playwright Chromium/Firefox/WebKit).
3. Click **Select elements**: a browser window opens at the URL; click elements to add them (column name, extract type: text/attribute/html).
4. Click **Run scrape** to extract data and save one CSV per run under the output directory (set in **File → Settings**).
