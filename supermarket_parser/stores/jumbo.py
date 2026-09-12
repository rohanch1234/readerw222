"""Jumbo (jumbo.com) parser.

Uses Jumbo's public mobile-app search API. Like Albert Heijn, this is not an
official/documented partner API — see the module note in
``albert_heijn.py`` for the same caveats (fields matched defensively,
rate-limited, may need updating if Jumbo changes their API).

Reference JSON shape this was written against lives in
``tests/fixtures/jumbo_search_response.json``.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ..models import Product
from .base import StoreParser

SEARCH_URL = "https://mobileapi.jumbo.com/v17/search"


def _first(d: dict, *keys: str) -> Any:
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return None


def _cents_to_euros(amount: Any) -> Optional[float]:
    if amount is None:
        return None
    return round(float(amount) / 100.0, 2)


class JumboParser(StoreParser):
    store_id = "jumbo"
    display_name = "Jumbo"

    def search(self, query: str, limit: int = 50) -> List[Product]:
        products: List[Product] = []
        offset = 0
        page_size = min(limit, 30) or 30

        while len(products) < limit:
            self.rate_limiter.wait()
            resp = self.session.get(
                SEARCH_URL,
                params={"q": query, "offset": offset, "limit": page_size},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            products_block = data.get("products", {})
            raw_products = products_block.get("data", [])
            if not raw_products:
                break

            for raw in raw_products:
                product = self._parse_product(raw)
                if product is not None:
                    products.append(product)
                if len(products) >= limit:
                    break

            total_count = products_block.get("count", offset + len(raw_products))
            offset += len(raw_products)
            if offset >= total_count:
                break

        return products[:limit]

    @staticmethod
    def _parse_product(raw: dict) -> Optional[Product]:
        product_id = _first(raw, "id", "sku")
        title = _first(raw, "title", "name")
        if product_id is None or not title:
            return None

        prices = raw.get("prices", {}) if isinstance(raw.get("prices"), dict) else {}
        price_block = prices.get("price") or {}
        promo_block = prices.get("promoPrice") or {}
        unit_block = prices.get("pricePerUnit") or {}

        current_amount = price_block.get("amount")
        promo_amount = promo_block.get("amount")

        # If there's an active promo, that's the current shelf price and the
        # regular price becomes the "was" price.
        if promo_amount is not None:
            current_price = _cents_to_euros(promo_amount)
            was_price = _cents_to_euros(current_amount)
        else:
            current_price = _cents_to_euros(current_amount)
            was_price = None

        unit_price = None
        unit_amount = (unit_block.get("price") or {}).get("amount")
        if unit_amount is not None and unit_block.get("unit"):
            unit_price = f"€{_cents_to_euros(unit_amount):.2f}/{unit_block['unit']}"

        image_url = None
        image_info = raw.get("imageInfo", {}) if isinstance(raw.get("imageInfo"), dict) else {}
        primary_views = image_info.get("primaryView") or []
        if primary_views and isinstance(primary_views[0], dict):
            image_url = primary_views[0].get("url")

        link = raw.get("link")
        product_url = f"https://www.jumbo.com{link}" if link else None

        return Product(
            store="jumbo",
            store_product_id=str(product_id),
            name=str(title),
            brand=_first(raw, "brand"),
            price=current_price,
            was_price=was_price,
            unit_size=_first(raw, "quantity", "unitSize"),
            unit_price=unit_price,
            category=_first(raw, "category"),
            image_url=image_url,
            product_url=product_url,
            available=bool(raw.get("available", True)),
        )
