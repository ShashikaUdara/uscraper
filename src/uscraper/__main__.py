"""Entry point for uscraper (GUI will be added in a later phase)."""
from uscraper.db import ensure_db


def main() -> None:
    # Ensure DB exists and schema is applied (for CLI/startup)
    conn = ensure_db()
    conn.close()
    print("uscraper: DB ready. GUI not yet implemented.")


if __name__ == "__main__":
    main()
