import json
from pathlib import Path
from unittest.mock import MagicMock

from supermarket_parser.stores.albert_heijn import AlbertHeijnParser

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_search_parses_products_from_fixture():
    parser = AlbertHeijnParser()

    auth_payload = {"access_token": "fake-token", "expires_in": 300}
    search_payload = json.loads((FIXTURES / "ah_search_response.json").read_text())

    parser.session.post = MagicMock(return_value=_fake_response(auth_payload))
    parser.session.get = MagicMock(return_value=_fake_response(search_payload))

    products = parser.search("melk", limit=10)

    assert len(products) == 2

    milk = products[0]
    assert milk.store == "albert_heijn"
    assert milk.store_product_id == "522210"
    assert milk.name == "AH Halfvolle melk"
    assert milk.price == 1.19
    assert milk.was_price == 1.19
    assert milk.on_sale is False
    assert milk.unit_size == "1 l"
    assert milk.image_url.endswith("AHI_522210.png")
    assert milk.product_url == "https://www.ah.nl/producten/product/wi522210"
    assert milk.available is True

    discounted = products[1]
    assert discounted.price == 1.39
    assert discounted.was_price == 1.69
    assert discounted.on_sale is True


def test_token_is_reused_across_searches():
    parser = AlbertHeijnParser()
    auth_payload = {"access_token": "fake-token", "expires_in": 300}
    search_payload = {"products": [], "page": {"totalPages": 1}}

    parser.session.post = MagicMock(return_value=_fake_response(auth_payload))
    parser.session.get = MagicMock(return_value=_fake_response(search_payload))

    parser.search("melk", limit=5)
    parser.search("brood", limit=5)

    assert parser.session.post.call_count == 1  # auth only happens once
    assert parser.session.get.call_count == 2
