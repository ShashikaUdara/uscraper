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
