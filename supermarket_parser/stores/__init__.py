"""Registry of available store parsers."""

from .albert_heijn import AlbertHeijnParser
from .base import StoreParser
from .jumbo import JumboParser
from .plus import PlusParser

STORE_REGISTRY: dict[str, type[StoreParser]] = {
    AlbertHeijnParser.store_id: AlbertHeijnParser,
    JumboParser.store_id: JumboParser,
    PlusParser.store_id: PlusParser,
}

__all__ = [
    "StoreParser",
    "AlbertHeijnParser",
    "JumboParser",
    "PlusParser",
    "STORE_REGISTRY",
]
