"""Plus (plus.nl) parser — TEMPLATE, selectors need verification.

Plus's search results are rendered client-side, so this uses the
Playwright-based :class:`GenericPlaywrightParser` instead of a JSON API.

This environment has no outbound network access to plus.nl, so the
selectors below could not be inspected/verified against the live site.
Before relying on this:

1. Open https://www.plus.nl/zoeken?trefwoord=melk in a browser.
2. Open devtools → Elements, inspect a product tile, and update the
   selectors in ``PlusParser.config`` to match what you actually see.
3. Run ``python -m supermarket_parser.cli --store plus --query melk`` and
   check the output looks right.

Once verified, the same pattern (copy this file, adjust the URL template
and selectors) works for other JS-rendered stores like Coop, Spar, Dirk,
Aldi or Lidl NL.
"""

from __future__ import annotations

from .generic_html import GenericPlaywrightParser, ScraperConfig


class PlusParser(GenericPlaywrightParser):
    store_id = "plus"
    display_name = "Plus"

    config = ScraperConfig(
        search_url_template="https://www.plus.nl/zoeken?trefwoord={query}",
        wait_for_selector="[data-test-id='product-tile']",
        product_selector="[data-test-id='product-tile']",
        name_selector="[data-test-id='product-title']",
        price_selector="[data-test-id='product-price']",
        unit_size_selector="[data-test-id='product-content-size']",
        image_selector="img",
        link_selector="a",
        base_url="https://www.plus.nl",
    )
