# Supermarket price parser

Fetches product/price data from Dutch supermarket websites and saves it as
normalized JSON (+ CSV), for use in a price-comparison website/app.

## Status

| Store | How it works | Status |
|---|---|---|
| Albert Heijn | AH's public mobile-app JSON API | Implemented (`stores/albert_heijn.py`) |
| Jumbo | Jumbo's public mobile-app JSON API | Implemented (`stores/jumbo.py`) |
| Plus | JS-rendered search page (Playwright) | Template only — **selectors need verification**, see below |
| Others (Coop, Spar, Dirk, Aldi, Lidl NL, ...) | Same `GenericPlaywrightParser` pattern as Plus | Not implemented yet — copy `stores/plus.py` |

Albert Heijn and Jumbo don't publish an official developer API; this uses
the same undocumented endpoints their own apps call (widely known/used for
this purpose). That means:

- No API key needed, but the endpoints can change without notice — if a
  parser suddenly returns 0 products, the JSON shape likely changed
  (see the "if this breaks" note in each store's file).
- **Respect the sites.** This is throttled by default (~1 request/second,
  see `supermarket_parser/http.py`) and identifies itself with a normal
  browser-like User-Agent. Don't remove the rate limiting, don't hammer
  the sites, and check `robots.txt` / terms of service before using this
  for anything beyond personal/educational use.

Plus (and most other Dutch supermarkets) render search results with
JavaScript, so they need a real browser (Playwright) rather than a plain
HTTP request. This environment couldn't reach plus.nl to inspect its
current DOM, so `stores/plus.py` ships as a **template with placeholder
CSS selectors** — see the instructions in that file for how to verify/fix
them (open devtools on the live site, 10 minutes of work). Once that's
done, the same pattern works for Coop, Spar, Dirk, Aldi, Lidl NL, etc. —
copy `plus.py`, change the URL + selectors.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# only if you'll use Plus/other JS-rendered stores:
pip install playwright
playwright install chromium
```

## Usage

```bash
# Scrape AH + Jumbo for a broad grocery basket, save under ./data
python -m supermarket_parser.cli --store albert_heijn jumbo

# Custom search terms / store(s) / result limit
python -m supermarket_parser.cli \
    --store albert_heijn \
    --query melk kaas koffie \
    --limit 50 \
    --out data

# List available store ids
python -m supermarket_parser.cli --list-stores
```

Each run writes, per store:

```
data/
  albert_heijn/
    2026-09-12T120000Z.json   # one snapshot per run (history)
    latest.json               # always the most recent snapshot
  jumbo/
    ...
  latest_all.json             # every store's latest.json, merged
  latest_all.csv              # same data as CSV
```

`latest_all.json` is what a comparison website/app should load — it's a
flat list of products across all stores, e.g.:

```json
{
  "store": "albert_heijn",
  "store_product_id": "522210",
  "name": "AH Halfvolle melk",
  "price": 1.19,
  "was_price": null,
  "currency": "EUR",
  "brand": "AH",
  "unit_size": "1 l",
  "unit_price": "€1.19 per l",
  "category": "Zuivel, plantaardig en eieren",
  "image_url": "https://static.ah.nl/dam/product/AHI_522210.png",
  "product_url": "https://www.ah.nl/producten/product/wi522210",
  "available": true,
  "scraped_at": "2026-09-12T12:00:00+00:00"
}
```

### Matching the same product across stores

Each `Product` has a `match_key` property (`name` + `unit_size`,
lowercased/slugified) as a starting point for "is this the same product at
different stores" matching — e.g. use it to group `latest_all.json` rows
by `match_key` on the comparison site. It's a heuristic (no barcode/GTIN
is exposed by these APIs), so expect some near-duplicates; refine as
needed once you see real data.

### Automating runs

To keep prices fresh, schedule the CLI (e.g. a cron job or GitHub Action)
to run periodically, e.g. daily:

```
0 6 * * * cd /path/to/repo && .venv/bin/python -m supermarket_parser.cli --out data
```

Since every run also keeps a timestamped snapshot, you get price history
for free — useful for a "price over time" chart on the website later.

## Running tests

Tests mock all HTTP calls (using fixture JSON in `tests/fixtures/`) so
they run offline and don't hit the real sites:

```bash
pip install pytest
pytest
```

## Project layout

```
supermarket_parser/
  models.py          Product dataclass (the normalized schema)
  http.py             shared requests session + rate limiter
  storage.py          saving snapshots as JSON/CSV
  cli.py               command-line entry point
  stores/
    base.py            StoreParser interface every store implements
    albert_heijn.py     AH JSON API parser
    jumbo.py             Jumbo JSON API parser
    generic_html.py     reusable Playwright+BeautifulSoup base for JS-rendered stores
    plus.py              Plus parser built on generic_html (selectors need verification)
tests/
  fixtures/            sample API responses used by the tests
```

## Extending to another store

1. Check whether the store has a JSON API like AH/Jumbo: open the store's
   site, devtools → Network → XHR, search for a product, and see if a
   `fetch`/`XHR` request returns JSON. If so, copy `stores/jumbo.py` as a
   starting point.
2. Otherwise, copy `stores/plus.py` + fill in `ScraperConfig` selectors
   for that store (JS-rendered, needs Playwright).
3. Register the new class in `supermarket_parser/stores/__init__.py`'s
   `STORE_REGISTRY`.
4. Add a fixture + test like `tests/test_jumbo.py`.
