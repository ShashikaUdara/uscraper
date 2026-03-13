# Packaging uscraper for Ubuntu

## pip install (recommended)

Users can install with pip in a venv; see [../docs/INSTALL.md](../docs/INSTALL.md). No packaging step required.

## Optional: Build a .deb package

Requires: `stdeb` (`pip install stdeb`), `dpkg`, and standard build tools.

From project root:

```bash
# Build source distribution
pip install build
python -m build --sdist

# Build .deb (installs stdeb if needed)
./packaging/build_deb.sh
# Output: packaging/deb_dist/python3-uscraper_*.deb
```

Or use the Makefile:

```bash
make dist-deb
```

The resulting .deb depends on Python 3 and will install the uscraper package. Users still need to install system dependencies (python3-tk, Playwright libs) as in INSTALL.md.

## Optional: Standalone executable (PyInstaller)

Requires: `pyinstaller` (`pip install pyinstaller`).

```bash
make dist-standalone
# Output: dist/uscraper/uscraper (or uscraper.exe on Windows)
```

This bundles Python and dependencies; Tkinter and Playwright system libs may still be required on the target system depending on the build.
