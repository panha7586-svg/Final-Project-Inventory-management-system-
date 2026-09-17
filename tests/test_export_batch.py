
from __future__ import annotations

from pathlib import Path

from utils.batch_utils import batch_adjust_stock, import_products_from_csv
from utils.export_utils import export_products_to_csv, export_transactions_to_csv


def test_csv_export_and_batch_operations(inventory, tmp_path: Path) -> None:
    product = inventory.add_product("Keyboard", "KEY-1", "Accessories", 5, 20, 35)

    product_csv = tmp_path / "products.csv"
    transaction_csv = tmp_path / "transactions.csv"
    export_products_to_csv(inventory.get_all_products(True), product_csv)
    export_transactions_to_csv(inventory.get_all_transactions(), transaction_csv)

    assert "KEY-1" in product_csv.read_text(encoding="utf-8-sig")
    assert "STOCK_IN" in transaction_csv.read_text(encoding="utf-8-sig")

    import_csv = tmp_path / "import.csv"
    import_csv.write_text(
        "name,sku,category,quantity,cost_price,selling_price,reorder_level\n"
        "Monitor,MON-1,Displays,3,100,150,2\n"
        "BadRow,,Displays,1,10,20,2\n",
        encoding="utf-8",
    )
    result = import_products_from_csv(import_csv, inventory)
    assert result["count"] == 1
    assert len(result["errors"]) == 1

    adjustment_result = batch_adjust_stock(
        [
            {"sku": product.sku, "quantity": 2, "performed_by": "admin"},
            {"sku": "missing", "quantity": 1},
        ],
        inventory,
    )
    assert adjustment_result["count"] == 1
    assert len(adjustment_result["errors"]) == 1
    assert inventory.get_product_by_sku(product.sku).quantity == 7
