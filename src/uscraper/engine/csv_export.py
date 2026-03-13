"""
CSV export: write extracted rows to a single CSV file per run.
UTF-8 encoding; one header row from column names.
"""
import csv
from pathlib import Path
from typing import Any, Dict, List, Sequence


def write_rows_to_csv(
    path: Path | str,
    rows: List[Dict[str, Any]],
    column_order: Sequence[str],
) -> int:
    """
    Write rows to a CSV file. Uses column_order for header and column order.
    Returns the number of data rows written (excluding header).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(column_order), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)
