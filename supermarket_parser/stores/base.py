"""Common interface every store parser implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..http import RateLimiter, build_session
from ..models import Product


class StoreParser(ABC):
    """Base class for a single supermarket's parser.

    Subclasses implement :meth:`search` (query -> products) and may override
    :meth:`fetch_categories`/:meth:`fetch_all` for full-catalog crawls.
    """

    #: machine-friendly id, used in filenames and the ``store`` field
    store_id: str = "base"
    #: human-friendly name
    display_name: str = "Base store"

    def __init__(self, min_interval: float = 1.0):
        self.session = build_session()
        self.rate_limiter = RateLimiter(min_interval=min_interval)

    @abstractmethod
    def search(self, query: str, limit: int = 50) -> List[Product]:
        """Return products matching a free-text search query."""
        raise NotImplementedError

    def search_many(self, queries: Iterable[str], limit: int = 50) -> List[Product]:
        """Run :meth:`search` for several queries and de-duplicate results."""
        seen: dict[str, Product] = {}
        for query in queries:
            for product in self.search(query, limit=limit):
                key = (product.store, product.store_product_id)
                seen[key] = product
        return list(seen.values())
