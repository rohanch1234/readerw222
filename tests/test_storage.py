import json

from supermarket_parser.models import Product
from supermarket_parser.storage import save_products, write_combined_latest


def test_save_products_and_combine(tmp_path):
    ah_products = [
        Product(store="albert_heijn", store_product_id="1", name="Melk", price=1.19),
    ]
    jumbo_products = [
        Product(store="jumbo", store_product_id="2", name="Melk", price=1.09),
    ]

    save_products(ah_products, "albert_heijn", tmp_path)
    save_products(jumbo_products, "jumbo", tmp_path)

    assert (tmp_path / "albert_heijn" / "latest.json").exists()
    assert (tmp_path / "jumbo" / "latest.json").exists()
    # exactly one timestamped snapshot per store as well
    assert len(list((tmp_path / "albert_heijn").glob("*.json"))) == 2

    combined_path = write_combined_latest(tmp_path)
    combined = json.loads(combined_path.read_text())

    assert len(combined) == 2
    assert {p["store"] for p in combined} == {"albert_heijn", "jumbo"}
    assert (tmp_path / "latest_all.csv").exists()
