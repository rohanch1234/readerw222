"""Saving scraped products to disk.

Output layout (under the given output directory, default ``data/``)::

    data/
      albert_heijn/
        2026-09-12T120000Z.json   <- one snapshot per run
        latest.json               <- always overwritten with the newest run
      jumbo/
        ...
      latest_all.json             <- every store's latest snapshot, combined
      latest_all.csv              <- same data, flattened to CSV

``latest_all.json`` is the file a price-comparison website/app would load.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from .models import Product


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def save_products(products: List[Product], store_id: str, out_dir: Path) -> Path:
    """Write one timestamped snapshot + refresh latest.json for a store."""
    store_dir = out_dir / store_id
    store_dir.mkdir(parents=True, exist_ok=True)

    payload = [p.to_dict() for p in products]

    snapshot_path = store_dir / f"{_timestamp_slug()}.json"
    snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    latest_path = store_dir / "latest.json"
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    return snapshot_path


def write_combined_latest(out_dir: Path) -> Path:
    """Merge every store's latest.json into one file (+ CSV) for the website."""
    combined: List[dict] = []
    for latest_path in sorted(out_dir.glob("*/latest.json")):
        combined.extend(json.loads(latest_path.read_text()))

    combined_json = out_dir / "latest_all.json"
    combined_json.write_text(json.dumps(combined, indent=2, ensure_ascii=False))

    combined_csv = out_dir / "latest_all.csv"
    _write_csv(combined, combined_csv)

    return combined_json


def _write_csv(rows: Iterable[dict], path: Path) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
