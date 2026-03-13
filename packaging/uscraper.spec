# PyInstaller spec for uscraper (optional standalone build).
# Run from project root: pyinstaller packaging/uscraper.spec
# Requires: pip install pyinstaller, and venv with uscraper installed.

# Run with: pyinstaller --specpath packaging packaging/uscraper.spec
# Or from project root: .venv/bin/pyinstaller packaging/uscraper.spec

a = Analysis(
    ['src/uscraper/__main__.py'],
    pathex=['src'],
    hiddenimports=[
        'uscraper',
        'uscraper.gui',
        'uscraper.gui.main_window',
        'uscraper.gui.dialogs',
        'uscraper.db',
        'uscraper.engine',
        'uscraper.engine.picker',
        'uscraper.engine.runner',
        'uscraper.engine.playwright_driver',
        'uscraper.engine.csv_export',
        'uscraper.engine.selector',
        'uscraper.browser_install',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='uscraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console for GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
