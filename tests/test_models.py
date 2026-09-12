from supermarket_parser.models import Product, slugify


def test_slugify_normalizes_text():
    assert slugify("AH Halfvolle melk, 1L!") == "ah-halfvolle-melk-1l"
    assert slugify("Café  crème  ") == "cafe-creme"


def test_match_key_combines_name_and_size():
    p = Product(store="jumbo", store_product_id="1", name="Halfvolle melk", price=1.19, unit_size="1 l")
    assert p.match_key == "halfvolle-melk-1-l"


def test_on_sale():
    p = Product(store="jumbo", store_product_id="1", name="X", price=1.0, was_price=1.5)
    assert p.on_sale is True

    p2 = Product(store="jumbo", store_product_id="1", name="X", price=1.5, was_price=1.5)
    assert p2.on_sale is False
