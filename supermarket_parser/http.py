"""Shared HTTP helpers: a polite, retrying requests session.

Centralizing this keeps every store parser rate-limited and identifiable,
and makes it easy to swap in caching/backoff behavior in one place.
"""

from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter, Retry

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; supermarket-price-parser/0.1; "
    "+personal price-comparison project)"
)


def build_session(user_agent: str = DEFAULT_USER_AGENT) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})

    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class RateLimiter:
    """Sleeps as needed so requests are spaced at least `min_interval` apart.

    Being a good citizen: supermarket sites are not designed for scraping
    traffic, so every store parser should throttle itself.
    """

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()
