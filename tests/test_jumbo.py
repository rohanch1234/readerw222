import json
from pathlib import Path
from unittest.mock import MagicMock

from supermarket_parser.stores.jumbo import JumboParser

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_search_parses_products_from_fixture():
    parser = JumboParser()
    payload = json.loads((FIXTURES / "jumbo_search_response.json").read_text())
    parser.session.get = MagicMock(return_value=_fake_response(payload))

    products = parser.search("melk", limit=10)

    assert len(products) == 2

    milk = products[0]
    assert milk.store == "jumbo"
    assert milk.store_product_id == "123456"
    assert milk.name == "Halfvolle melk"
    assert milk.price == 1.19
    assert milk.was_price is None
    assert milk.unit_price == "€1.19/l"
    assert milk.product_url == "https://www.jumbo.com/producten/123456/halfvolle-melk"

    discounted = products[1]
    assert discounted.price == 1.39       # promo price is the current price
    assert discounted.was_price == 1.69   # regular price becomes "was" price
    assert discounted.on_sale is True
