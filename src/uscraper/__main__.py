"""Entry point for uscraper — launches the desktop GUI."""
import sys


def main() -> None:
    try:
        from uscraper.logging_config import setup_logging
        setup_logging(console=True)
    except Exception:
        pass
    try:
        from uscraper.gui import run_gui
    except ImportError as e:
        if "tkinter" in str(e).lower() or "tk" in str(e).lower():
            print("uscraper: Tkinter not available. On Ubuntu install: sudo apt install python3-tk", file=sys.stderr)
        else:
            print(f"uscraper: Failed to load GUI: {e}", file=sys.stderr)
        sys.exit(1)
    run_gui()


if __name__ == "__main__":
    main()
