"""Reusable scraper for stores that don't expose a simple JSON API.

Albert Heijn and Jumbo have (undocumented but stable) JSON search APIs, so
they get dedicated parsers. Many other Dutch supermarkets (Plus, Coop,
Spar, Dirk, ...) render their search results with JavaScript, so a plain
``requests`` + HTML-parse approach won't see any products — the page needs
to actually run in a browser first.

``GenericPlaywrightParser`` is a small, configurable base for that case:
subclass it, fill in a :class:`ScraperConfig` with the store's search URL
and CSS selectors, and you get a working :meth:`search`.

IMPORTANT: the exact CSS selectors for a given store must be found by
opening the store's search page in a real browser and inspecting the DOM
(devtools → Elements). This environment has no outbound access to
supermarket websites, so the selectors below are placeholders/best-effort —
verify and adjust them against the live site before relying on the output.
Playwright is an optional dependency; install it with
``pip install playwright && playwright install chromium`` to use this.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..models import Product
from .base import StoreParser


@dataclass
class ScraperConfig:
    search_url_template: str        # e.g. "https://example.nl/zoeken?q={query}"
    wait_for_selector: str          # a selector present once results have loaded
    product_selector: str           # one selector per product card
    name_selector: str
    price_selector: str
    unit_size_selector: Optional[str] = None
    image_selector: Optional[str] = None
    link_selector: Optional[str] = None
    base_url: str = ""              # prefixed onto relative product links


class GenericPlaywrightParser(StoreParser):
    """Base class for JS-rendered store search pages.

    Subclasses set ``store_id``, ``display_name`` and ``config``.
    """

    config: ScraperConfig

    def search(self, query: str, limit: int = 50) -> List[Product]:
        try:
            from bs4 import BeautifulSoup
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "GenericPlaywrightParser needs 'playwright' and 'beautifulsoup4'. "
                "Install with: pip install playwright beautifulsoup4 && "
                "playwright install chromium"
            ) from exc

        self.rate_limiter.wait()
        url = self.config.search_url_template.format(query=query)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(user_agent=self.session.headers.get("User-Agent"))
            page.goto(url, timeout=30000)
            page.wait_for_selector(self.config.wait_for_selector, timeout=15000)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.config.product_selector)[:limit]

        products: List[Product] = []
        for i, card in enumerate(cards):
            product = self._parse_card(card, index=i)
            if product is not None:
                products.append(product)
        return products

    def _parse_card(self, card, index: int) -> Optional[Product]:
        cfg = self.config

        name_el = card.select_one(cfg.name_selector)
        price_el = card.select_one(cfg.price_selector)
        if name_el is None or price_el is None:
            return None

        name = name_el.get_text(strip=True)
        price = self._parse_price(price_el.get_text(strip=True))

        unit_size = None
        if cfg.unit_size_selector:
            el = card.select_one(cfg.unit_size_selector)
            unit_size = el.get_text(strip=True) if el else None

        image_url = None
        if cfg.image_selector:
            el = card.select_one(cfg.image_selector)
            if el is not None:
                image_url = el.get("src") or el.get("data-src")

        product_url = None
        if cfg.link_selector:
            el = card.select_one(cfg.link_selector)
            if el is not None and el.get("href"):
                href = el["href"]
                product_url = href if href.startswith("http") else cfg.base_url + href

        # Store products usually don't have a stable numeric id available in
        # the search HTML, so fall back to a positional id derived from the
        # product URL (or the name) — good enough to dedupe within one run.
        store_product_id = product_url or f"{self.store_id}-{index}-{name}"

        return Product(
            store=self.store_id,
            store_product_id=store_product_id,
            name=name,
            price=price,
            unit_size=unit_size,
            image_url=image_url,
            product_url=product_url,
        )

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        """Parse "€ 2,19", "2.19", "€2,19" style strings into a float."""
        cleaned = text.replace("€", "").strip()
        cleaned = cleaned.replace(".", "").replace(",", ".") if "," in cleaned else cleaned
        try:
            return float(cleaned)
        except ValueError:
            return None
