
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Any

from models.product import Product
from models.transaction import Transaction


def _write_csv(filename: str | Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_products_to_csv(products: Iterable[Product], filename: str | Path) -> Path:
    fields = [
        "product_id", "name", "sku", "category", "quantity", "cost_price",
        "selling_price", "supplier_id", "reorder_level", "active", "created_at", "updated_at",
    ]
    return _write_csv(filename, fields, (product.to_dict() for product in products))


def export_transactions_to_csv(transactions: Iterable[Transaction], filename: str | Path) -> Path:
    fields = [
        "transaction_id", "product_id", "tx_type", "quantity", "unit_price",
        "supplier_id", "performed_by", "note", "timestamp",
    ]
    return _write_csv(filename, fields, (transaction.to_dict() for transaction in transactions))
