# Installing uscraper on Ubuntu

## System requirements

- **Ubuntu** 22.04 LTS or 24.04 LTS (or similar Debian-based Linux)
- **Python** 3.10 or newer
- **Tkinter** (for the GUI): `python3-tk`
- **Playwright** system libraries (for browser automation): installed via `playwright install-deps`

## Quick install (recommended)

```bash
# 1. Clone or unpack the project, then from project root:

# 2. Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3 python3-venv python3-tk

# 3. Create venv and install uscraper
make venv
make install

# 4. Install Playwright system libraries (required for browser automation)
make install-deps

# 5. (Optional) Install Playwright browsers (Chromium, Firefox, WebKit)
#    You can also install from the app: select a browser and click "Install / Use"
make install-browsers

# 6. Run the application
make run
# or: .venv/bin/uscraper
```

## Step-by-step (without Make)

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m playwright install-deps    # system libs for Playwright
.venv/bin/python -m playwright install         # optional: download browsers
.venv/bin/uscraper
```

## First run

On first launch, uscraper will:

- Create `~/.config/uscraper/` and the SQLite database
- Seed the browser list (Chromium, Firefox, WebKit); install status is "pending" until you click **Install / Use** for a browser

No browser is installed automatically; install at least one from the app or run `make install-browsers`.

## Using the Picker

To choose which parts of a page to scrape:

1. Create or select a **profile**, enter the **URL**, and select a **browser** (install it if needed).
2. Click **Select elements**. A browser window opens at the URL.
3. **Click an element** on the page that you want to scrape. A dialog opens with:
   - **Element preview**: tag name, id/class, and a short text preview so you can confirm the right element.
   - **Selector**: the CSS selector (with a **Copy** button).
   - **Column name**: suggestions from the element (e.g. "link" for links, "image_src" for images) and existing profile columns; you can type a custom name.
   - **Extract**: "text", "attribute", or "html". For "attribute", choose the attribute from a dropdown showing `name → value`; use **View full** to see long values.
4. Click **OK** to add the element to the profile, or **Cancel** to skip. Close the browser when you are done picking elements.
5. Use **Run scrape** to run the profile and export data to CSV.

In the element-options dialog, **Enter** confirms and **Escape** cancels.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `No module named 'tkinter'` | Install Tkinter: `sudo apt install python3-tk` |
| Playwright browser fails to launch | Run `make install-deps` (or `python -m playwright install-deps`) to install system libraries |
| Browser not found | Run `make install-browsers` or use **Install / Use** in the app for the chosen browser |

## Packaging (optional)

- **pip / venv:** Use the steps above; no packaging needed.
- **.deb:** See `packaging/README.md` and `make dist-deb` (requires `stdeb`).
- **Standalone binary:** See `make dist-standalone` (requires `pyinstaller`).
