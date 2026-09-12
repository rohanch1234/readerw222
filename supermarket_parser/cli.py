"""Command-line entry point.

Examples
--------
Fetch a handful of grocery categories from AH and Jumbo::

    python -m supermarket_parser.cli \\
        --store albert_heijn jumbo \\
        --query melk brood kaas eieren \\
        --limit 40 \\
        --out data

List available stores::

    python -m supermarket_parser.cli --list-stores
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from .stores import STORE_REGISTRY
from .storage import save_products, write_combined_latest

DEFAULT_QUERIES = [
    "melk", "brood", "kaas", "eieren", "boter", "yoghurt",
    "appels", "bananen", "aardappelen", "kip", "rijst", "pasta",
    "koffie", "thee", "bier", "wijn", "chips", "chocolade",
]


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape supermarket products/prices.")
    parser.add_argument(
        "--store",
        nargs="+",
        choices=list(STORE_REGISTRY.keys()),
        default=list(STORE_REGISTRY.keys()),
        help="Which store(s) to scrape (default: all registered stores).",
    )
    parser.add_argument(
        "--query",
        nargs="+",
        default=DEFAULT_QUERIES,
        help="Search terms to fetch (default: a broad grocery basket).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Max products per search term per store (default: 40).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data"),
        help="Output directory (default: ./data).",
    )
    parser.add_argument(
        "--list-stores",
        action="store_true",
        help="Print available store ids and exit.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.list_stores:
        for store_id, cls in STORE_REGISTRY.items():
            print(f"{store_id:15s} {cls.display_name}")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)

    for store_id in args.store:
        parser_cls = STORE_REGISTRY[store_id]
        print(f"[{store_id}] fetching {len(args.query)} search terms...")
        parser = parser_cls()
        try:
            products = parser.search_many(args.query, limit=args.limit)
        except Exception as exc:  # keep going even if one store fails
            print(f"[{store_id}] FAILED: {exc}", file=sys.stderr)
            continue

        snapshot_path = save_products(products, store_id, args.out)
        print(f"[{store_id}] saved {len(products)} products -> {snapshot_path}")

    combined_path = write_combined_latest(args.out)
    print(f"combined dataset -> {combined_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
