
from __future__ import annotations

import json

import pytest

from services.inventory_service import (
    DuplicateSKUError,
    InsufficientStockError,
)
from models.transaction import TransactionType


def test_add_product_persists_and_records_initial_stock(inventory) -> None:
    product = inventory.add_product("Keyboard", "KEY-1", "Accessories", 10, 20, 35)

    assert product.quantity == 10
    assert inventory.get_product_by_sku("key-1") is product
    assert len(inventory.get_all_transactions()) == 1
    assert inventory.get_all_transactions()[0].tx_type == TransactionType.STOCK_IN


def test_duplicate_sku_is_rejected(inventory) -> None:
    inventory.add_product("Keyboard", "KEY-1", "Accessories", 1, 20, 35)
    with pytest.raises(DuplicateSKUError):
        inventory.add_product("Another", "key-1", "Accessories", 1, 10, 15)


def test_stock_out_rejects_insufficient_quantity(inventory) -> None:
    product = inventory.add_product("Mouse", "M-1", "Accessories", 3, 10, 18)
    with pytest.raises(InsufficientStockError):
        inventory.stock_out(product.product_id, 4)
    assert inventory.get_product_by_id(product.product_id).quantity == 3


def test_stock_and_purchase_changes_are_audited(inventory) -> None:
    product = inventory.add_product("SSD", "SSD-1", "Storage", 5, 50, 80)
    inventory.stock_in(product.product_id, 2, unit_cost=52, performed_by="staff")
    inventory.stock_out(product.product_id, 3, unit_price=80, performed_by="sales")
    inventory.record_purchase(product.product_id, 4, 48, "supplier-1", performed_by="buyer")

    assert inventory.get_product_by_id(product.product_id).quantity == 8
    types = [tx.tx_type for tx in inventory.get_transactions_for_product(product.product_id)]
    assert types == [TransactionType.STOCK_IN, TransactionType.STOCK_IN, TransactionType.STOCK_OUT, TransactionType.PURCHASE]


def test_enhanced_search_filters_by_keyword_price_and_stock(inventory) -> None:
    inventory.add_product("Laptop Basic", "L-1", "Laptop", 5, 500, 700)
    inventory.add_product("Laptop Pro", "L-2", "Laptop", 20, 900, 1200)
    inventory.add_product("Mouse", "M-1", "Accessory", 30, 10, 30)

    results = inventory.search_products("Laptop", min_price=1000, min_stock=10, max_stock=25)
    assert [product.sku for product in results] == ["L-2"]


def test_enhanced_search_rejects_invalid_ranges(inventory) -> None:
    with pytest.raises(ValueError, match="Minimum price"):
        inventory.search_products(min_price=100, max_price=50)
    with pytest.raises(ValueError, match="Minimum stock"):
        inventory.search_products(min_stock=10, max_stock=2)


def test_soft_and_hard_delete(inventory, test_settings) -> None:
    product = inventory.add_product("Cable", "C-1", "Accessories", 2, 5, 10)
    inventory.soft_delete_product(product.product_id)
    assert inventory.get_all_products() == []
    assert inventory.get_all_products(include_inactive=True)[0].active is False

    inventory.hard_delete_product(product.product_id)
    assert inventory.get_all_products(include_inactive=True) == []
    raw = json.loads((test_settings.data_dir / test_settings.products_file).read_text(encoding="utf-8"))
    assert raw == []
