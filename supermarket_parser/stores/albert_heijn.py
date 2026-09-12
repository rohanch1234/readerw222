"""Albert Heijn (ah.nl) parser.

Uses AH's public mobile-app API (the same endpoints the "Appie" app calls).
It is not an official/documented partner API, so:

- Response fields are matched defensively (a couple of alternate key names
  are tried) because AH has changed the exact JSON shape over time.
- If AH changes the API again, :meth:`AlbertHeijnParser._parse_product` is
  the only place that needs updating — see ``tests/test_albert_heijn.py``
  for the JSON shape this was written against.
- Be polite: this parser rate-limits itself (see ``base.StoreParser``).
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from ..models import Product
from .base import StoreParser

AUTH_URL = "https://api.ah.nl/mobile-auth/v1/auth/token/anonymous"
SEARCH_URL = "https://api.ah.nl/mobile-services/product/search/v2"


def _first(d: dict, *keys: str) -> Any:
    """Return the first present, non-None value for any of `keys` in `d`."""
    for key in keys:
        if key in d and d[key] is not None:
            return d[key]
    return None


class AlbertHeijnParser(StoreParser):
    store_id = "albert_heijn"
    display_name = "Albert Heijn"

    def __init__(self, min_interval: float = 1.0):
        super().__init__(min_interval=min_interval)
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        self.rate_limiter.wait()
        resp = self.session.post(
            AUTH_URL,
            json={"clientId": "appie"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        # Refresh a little early to be safe.
        self._token_expires_at = time.monotonic() + data.get("expires_in", 300) - 30
        return self._token

    def search(self, query: str, limit: int = 50) -> List[Product]:
        token = self._get_token()
        products: List[Product] = []
        page = 0
        page_size = min(limit, 100) or 100

        while len(products) < limit:
            self.rate_limiter.wait()
            resp = self.session.get(
                SEARCH_URL,
                params={"query": query, "size": page_size, "page": page},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_products = data.get("products", [])
            if not raw_products:
                break

            for raw in raw_products:
                product = self._parse_product(raw)
                if product is not None:
                    products.append(product)
                if len(products) >= limit:
                    break

            total_pages = data.get("page", {}).get("totalPages", page + 1)
            page += 1
            if page >= total_pages:
                break

        return products[:limit]

    @staticmethod
    def _parse_product(raw: dict) -> Optional[Product]:
        product_id = _first(raw, "webshopId", "id")
        title = _first(raw, "title", "description")
        if product_id is None or not title:
            return None

        price_info = raw.get("priceInfo", {}) if isinstance(raw.get("priceInfo"), dict) else {}
        current_price = _first(raw, "currentPrice") or price_info.get("currentPrice")
        was_price = _first(raw, "priceBeforeBonus") or price_info.get("wasPrice")

        images = raw.get("images") or []
        image_url = None
        if images and isinstance(images, list) and isinstance(images[0], dict):
            image_url = images[0].get("url")
        elif isinstance(raw.get("image"), dict):
            image_url = raw["image"].get("url")

        category = _first(raw, "mainCategory", "category")

        available = raw.get("availableOnline", True)
        status = raw.get("orderAvailabilityStatus")
        if status:
            available = status == "IN_ASSORTMENT"

        return Product(
            store="albert_heijn",
            store_product_id=str(product_id),
            name=str(title),
            brand=_first(raw, "brand"),
            price=float(current_price) if current_price is not None else None,
            was_price=float(was_price) if was_price is not None else None,
            unit_size=_first(raw, "salesUnitSize", "unitSize"),
            unit_price=_first(raw, "unitPriceDescription"),
            category=category,
            image_url=image_url,
            product_url=f"https://www.ah.nl/producten/product/wi{product_id}",
            available=bool(available),
        )
