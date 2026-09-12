"""Normalized data model shared by every store parser."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def slugify(text: str) -> str:
    """Turn free text into a stable, comparable key.

    Used to build ``match_key`` so the same product can be recognized across
    different supermarkets even though each store spells/capitalizes/spaces
    the name a little differently.
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


@dataclass
class Product:
    """One product+price observation from one store, at one point in time."""

    store: str                      # e.g. "albert_heijn", "jumbo", "plus"
    store_product_id: str           # store's own internal product/SKU id
    name: str                       # product title as shown by the store
    price: Optional[float]          # current price in EUR, e.g. 2.19
    currency: str = "EUR"

    brand: Optional[str] = None
    was_price: Optional[float] = None      # price before discount, if on sale
    unit_size: Optional[str] = None        # e.g. "500 g", "1 L", "6 stuks"
    unit_price: Optional[str] = None       # e.g. "€4.38/kg"
    category: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    available: bool = True

    scraped_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def on_sale(self) -> bool:
        return self.was_price is not None and (
            self.price is not None and self.price < self.was_price
        )

    @property
    def match_key(self) -> str:
        """Normalized key for matching the "same" product across stores.

        This is a best-effort heuristic (name + unit size), good enough as a
        starting point for a comparison site; exact matching across stores
        usually needs a barcode/GTIN, which most store APIs don't expose.
        """
        base = f"{self.name} {self.unit_size or ''}"
        return slugify(base)

    def to_dict(self) -> dict:
        return asdict(self)
